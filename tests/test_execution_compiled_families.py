"""Complete original named families are the source-side differential reference."""

import hashlib
import json
import re
import sys

import pytest

import _pietto_sql_emission as emission
import _pietto_sql_float_cells as float_cells
import _pietto_sql_paired as paired_forms
from _pietto_execution_binding import proof_artifact
from _pietto_execution_compiled import retained_unmapped_source
from _pietto_execution_refinement import capabilities
from _pietto_execution_rows_cases import CASES, build
from _pietto_execution_guard_cases import manifest, case_preparation
from _pietto_plan_nested import (
    HEAD,
    LISTED,
    LISTED_KEPT,
    LISTED_PLACES,
    UNNEST_PARENT,
    emission_contract,
    project,
)
from _pietto_semantic_join_asof import CANONICAL, project_contract
import _pietto_semantic_relationship_rows as rows
from pietto._project.project_compiled_build import CompiledBuild, build_compiled
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_lowering import emit_compiled
from pietto._project.project_execution_template import (
    BindingError,
    bind_values,
    prepare_live_template,
)
from pietto._project.project_result_output import prepare_output
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_cli import POLICIES, emit_project

from _pietto_sql_emission import graft

from dataclasses import replace
from typing import Any
import _pietto_sql_emission as probe
from _pietto_sql_emission import S05_POSTGRES_BODY
from _pietto_sql_emission import emit_aggregate_composition
import _pietto_sql_emission_portable as portable
import _pietto_sql_emission_pure_boundary as pure
from pietto._project import project_compiled_schema as compiled_schema
from pietto._project import project_sql_emission_paired as pairing
from pietto._project.project_sql_emission_ast import SQLRowQuery
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", CASES)
def test_original_named_family_closure(tmp_path, target, case, variant):
    original = build(tmp_path / "source-build", target, case, variant)
    if original.status == "BLOCKED":
        assert original.artifact is None and original.blockers
        with pytest.raises(BindingError, match="^BINDING_ARTIFACT$"):
            build_compiled(original.artifact)
        return
    _compare(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("operator", ("is None", "is not None"))
def test_loaded_null_test_rehydrates_non_null_bool(tmp_path, target, operator):
    item = emission.fixture(target, "T_row_direct", "query_bind")
    source = (
        item["source"]
        if operator == "is None"
        else item["source"].replace(
            "missing = flag is None", "missing = flag " + operator
        )
    )
    checked, original = emission.build_case(
        tmp_path / operator.replace(" ", "-"),
        source,
        item["contract"],
        item["policy"],
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    built = build_compiled(original.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    candidate = emit_compiled(
        loaded, tuple(value.value for value in original.artifact.fixed_values)
    )
    assert candidate.rendered.sql == original.artifact.rendered.sql
    assert (" IS NOT NULL" if operator == "is not None" else " IS NULL") in (
        candidate.rendered.sql.decode()
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_abs_replays_from_compiled_input(tmp_path, target):
    """`abs` of an Int, a Float and a Decimal keeps its type and realization."""
    item = emission.fixture(target, "T_row_direct", "table_preserve")
    source = item["source"].split("table result:", 1)[0] + (
        "table result:\n    from rows\n    select:\n"
        "        widened = abs(id + 0)\n"
        "        ratio_size = abs(ratio)\n"
        "        money_size = abs(money)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    # The R2 refinement page verifier reads no scalar call yet (fails closed).
    _compare(original.artifact, refinement=False)


# Each scalar family's select lines and the SQL each target writes for it;
# MySQL project SQL refuses `concat`.
SCALAR_FAMILIES = {
    "typed_null": (
        "        plus = id + None\n        times = None * 2\n"
        "        negated = -(id + None)\n",
        {"postgres": "CAST(NULL AS pg_catalog.int8)", "mysql": "CAST(NULL AS SIGNED)"},
    ),
    "same_value": (
        "        both_null = same_value(nullif(id, id), nullif(id, id))\n"
        '        texts = same_value(text, nullif(text, "x"))\n'
        "        amounts = same_value(money, money)\n"
        "        typed = same_value(id + None, id)\n"
        "        floats = same_value(ratio, 1.5)\n",
        {"postgres": " IS NOT DISTINCT FROM ", "mysql": " <=> "},
    ),
    "concat": (
        '        joined = concat(text, "x", text)\n        nulled = concat(text, None)\n',
        {"postgres": " || "},
    ),
}


@pytest.mark.parametrize(
    "target,family", [(t, f) for f, (_, sql) in SCALAR_FAMILIES.items() for t in sql]
)
def test_scalar_families_replay_and_bind_their_live_template(tmp_path, target, family):
    """Int arithmetic with a typed NULL (D-12), `same_value` and PostgreSQL
    `concat` build, load and replay from compiled input, and their live
    template renders the emitted SQL and binds its WHERE literal."""
    body, sql = SCALAR_FAMILIES[family]
    item = emission.fixture(target, "T_row_direct", "query_bind")
    source = item["source"].split("query result:", 1)[0] + (
        "query result:\n    from rows\n    where id > 0\n    select:\n        id\n"
        + body
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    assert original.artifact is not None
    assert sql[target].encode() in original.artifact.rendered.sql
    # The R2 refinement page verifier reads no scalar call (REFINEMENT_NATIVE_SQL)
    # and no typed NULL (REFINEMENT_SCALAR) yet; both fail closed.
    _compare(original.artifact, refinement=False)
    assert _live(original.artifact).values[0] == 0


# The list operations of a row's collected list (S06): in SELECT items, over
# a list carried through a LEFT JOIN, in a row let and the WHERE, and over a
# parent imported from another module.
LIST_OPERATIONS = {
    "select": {"main.pietto": HEAD.format(target="postgres") + LISTED},
    "left_join_carrier": {"main.pietto": HEAD.format(target="postgres") + LISTED_KEPT},
    "let_where": {"main.pietto": HEAD.format(target="postgres") + LISTED_PLACES},
    "imported_parent": {
        "parent.pietto": HEAD.format(target="postgres")
        + UNNEST_PARENT
        + "export (\n    query parent,\n)\n",
        "main.pietto": 'from "parent.pietto" import (\n    query parent,\n)\n'
        + LISTED.removeprefix(UNNEST_PARENT),
    },
}


@pytest.mark.parametrize("policy", ("preserve", "bind-safe"))
@pytest.mark.parametrize("case", sorted(LIST_OPERATIONS))
def test_list_operations_replay_with_their_requirements(tmp_path, case, policy):
    """`len`, `sum` (the count included) and `any` over a collected list
    replay from compiled input with the live requirements: an element read
    `o.f` is a column read (R01) in both."""
    files = LIST_OPERATIONS[case]
    root = project(tmp_path / "project", files)
    document = json.loads(
        emission_contract(
            "postgres", "parent.pietto" if len(files) > 1 else "main.pietto"
        )
    )
    document["environment"] += [
        {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"},
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended",
        },
    ]
    (root / "contract.json").write_text(json.dumps(document), encoding="utf-8")
    outcome, _ = emit_project(
        root,
        "main.pietto",
        "query",
        "result",
        "postgres",
        "contract.json",
        POLICIES[policy],
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    _compare(outcome.artifact, refinement=False)


@pytest.mark.parametrize(
    "case,variant",
    (
        ("V_aggregate_blocked", "sum_direct"),
        ("V_row_blocked", "int_overflow"),
        ("V_row_blocked", "unary_overflow"),
    ),
)
def test_postgresql_checked_bigint_replays_from_compiled_input(tmp_path, case, variant):
    """Q1/Q2: SUM's bigint casts, a checked operation's clipped range and the
    target-checked evidence replay from compiled input."""
    original = build(tmp_path, "postgres", case, variant)
    assert original.status == "VERIFIED" and original.artifact is not None
    aggregate = case == "V_aggregate_blocked"
    candidate = _compare(original.artifact, refinement=not aggregate)
    if aggregate:
        # The R2 refinement page reads no aggregate cast yet, as for AVG:
        # it refuses the statement rather than page it.
        with pytest.raises(ValueError, match="^REFINEMENT_NATIVE_SQL$"):
            _compare_refinement(original.artifact)
    evidence = [r.evidence for r in original.artifact.generated_requirements]
    assert ("target_checked_signed64_narrowing",) in evidence
    assert [r.evidence for r in candidate.generated_requirements] == evidence


@pytest.mark.parametrize(
    "variant,evidence",
    (
        ("stddev_direct", ()),
        ("stddev_float", ("target_checked_binary64_overflow",)),
    ),
)
def test_postgresql_stddev_replays_from_compiled_input(tmp_path, variant, evidence):
    """Lane F: SQRT(CAST(VAR_SAMP(x) AS float8)), its Float result and the
    argument-keyed R13 evidence replay from compiled input."""
    original = build(tmp_path, "postgres", "V_aggregate_blocked", variant)
    assert original.status == "VERIFIED" and original.artifact is not None
    candidate = _compare(original.artifact, refinement=False)
    assert b"SQRT(CAST(VAR_SAMP(" in candidate.rendered.sql
    # The R2 refinement page reads no aggregate cast, as for SUM and AVG.
    with pytest.raises(ValueError, match="^REFINEMENT_NATIVE_SQL$"):
        _compare_refinement(original.artifact)
    aggregate = [
        r.evidence
        for r in original.artifact.generated_requirements
        if r.kind == "aggregate"
    ]
    assert aggregate == [evidence]
    assert [r.evidence for r in candidate.generated_requirements] == [
        r.evidence for r in original.artifact.generated_requirements
    ]


BINARY64 = ("target_checked_binary64_overflow",)


@pytest.mark.parametrize(
    "variant,evidence", (("spread_direct", ()), ("spread_float", BINARY64))
)
def test_postgresql_variance_and_population_deviation_replay_from_compiled_input(
    tmp_path, variant, evidence
):
    """CAST(VAR_SAMP(x) AS float8), CAST(VAR_POP(x) AS float8) and the SQRT
    of the latter, their Float results and the argument-keyed R13 evidence
    replay from compiled input."""
    original = build(tmp_path, "postgres", "V_aggregate_blocked", variant)
    assert original.status == "VERIFIED" and original.artifact is not None
    candidate = _compare(original.artifact, refinement=False)
    sql = candidate.rendered.sql
    assert b"CAST(VAR_SAMP(" in sql and b"SQRT(CAST(VAR_SAMP(" not in sql
    assert sql.count(b"CAST(VAR_POP(") == 2 and sql.count(b"SQRT(CAST(VAR_POP(") == 1
    with pytest.raises(ValueError, match="^REFINEMENT_NATIVE_SQL$"):
        _compare_refinement(original.artifact)
    assert [
        r.evidence
        for r in original.artifact.generated_requirements
        if r.kind == "aggregate"
    ] == [evidence] * 3
    assert [r.evidence for r in candidate.generated_requirements] == [
        r.evidence for r in original.artifact.generated_requirements
    ]


@pytest.mark.parametrize(
    "target,variant,evidence",
    (
        ("postgres", "sum_float", [BINARY64]),
        ("postgres", "avg_float", [BINARY64]),
        ("postgres", "postgres_carriers", [()] * 5),
        ("mysql", "postgres_carriers", [()] * 5),
        (
            "postgres",
            "inline_arguments",
            [("target_checked_signed64_narrowing",), (), ()],
        ),
        ("postgres", "count_distinct_tuple", [()] * 4),
    ),
)
def test_aggregate_parity_replays_from_compiled_input(
    tmp_path, target, variant, evidence
):
    """S16: an uncast float8 SUM/AVG, a Text, Bool, Float or Decimal count,
    distinct count or extreme (on MySQL too) and an aggregate over a row
    expression replay from compiled input with their argument-keyed R13
    evidence."""
    original = build(tmp_path, target, "V_aggregate_blocked", variant)
    assert original.status == "VERIFIED" and original.artifact is not None
    candidate = _compare(original.artifact, refinement=False)
    assert [
        r.evidence
        for r in original.artifact.generated_requirements
        if r.kind == "aggregate"
    ] == evidence
    assert [r.evidence for r in candidate.generated_requirements] == [
        r.evidence for r in original.artifact.generated_requirements
    ]


def _nullable_ratio(tmp_path, body, header="query result:"):
    item = probe.nullable_ratio_fixture("mysql", header + "\n    from agg\n" + body)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    return outcome


@pytest.mark.parametrize(
    "function,spelling",
    (
        ("stddev", "STDDEV_SAMP"),
        ("variance", "VAR_SAMP"),
        ("pvariance", "VAR_POP"),
        ("pstdev", "STDDEV_POP"),
    ),
)
def test_mysql_float_statistic_cell_replays_from_compiled_input(
    tmp_path, function, spelling
):
    """Phase77 S05: the MySQL statistic of one nullable DOUBLE field alone,
    its nullable DOUBLE result and its binary64 evidence replay from
    compiled input."""
    original = _nullable_ratio(
        tmp_path, f"    select:\n        d = {function}(ratio)\n"
    )
    candidate = _compare(original.artifact, refinement=False)
    assert f"(SELECT {spelling}(`s0`.`ratio value`) AS".encode() in (
        candidate.rendered.sql
    )
    assert [
        r.evidence for r in candidate.generated_requirements if r.kind == "aggregate"
    ] == [BINARY64]


def _renamed_statistic(tmp_path, body, header="query result:"):
    """A loaded MySQL `max` bundle whose value is renamed `stddev`, and that
    value's address."""
    from pietto._project.project_compiled_schema import (
        FIELDS,
        Record,
        content_pin,
        encode,
    )

    built = build_compiled(_nullable_ratio(tmp_path, body, header).artifact)
    (value,) = (
        r
        for r in built.root.description.records
        if r.address.kind == "aggregate_value" and r.get("function") == "max"
    )
    values = list(value.values)
    values[FIELDS["aggregate_value"].index("function")] = "stddev"
    forged = Record(value.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (name, tuple(forged if r.address == forged.address else r for r in members))
            for name, members in built.root.description.members
        ),
    )
    raw = encode(description)
    root = load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    return root, forged.address


@pytest.mark.parametrize(
    "header,body,accepted",
    (
        ("query result:", "    select:\n        d = max(ratio)\n", True),
        (
            "query result:",
            "    group by key\n    select:\n        key\n        d = max(ratio)\n",
            False,
        ),
        (
            "query result:",
            "    select:\n        lo = min(ratio)\n        d = max(ratio)\n",
            False,
        ),
        (
            "query result:",
            "    where rid > 1\n    select:\n        d = max(ratio)\n",
            False,
        ),
        ("query result(low: Int):", "    select:\n        d = max(ratio)\n", False),
        ("query result:", "    select:\n        d = max(ratio)\n    limit 1\n", False),
    ),
)
def test_a_compiled_mysql_statistic_is_judged_by_its_records(
    tmp_path, header, body, accepted
):
    """A MySQL `max` bundle whose value is renamed `stddev` replays as the S05
    cell only where its records hold the cell's structure; renamed in a
    grouped, two-value, filtered or limited aggregate, or in a query that
    declares a header parameter it never reads, it stays refused."""
    from pietto._project.project_compiled_schema import CompiledError

    root, _ = _renamed_statistic(tmp_path, body, header)
    if not accepted:
        with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_ARGUMENT$"):
            emit_compiled(root, ())
        return
    assert b"(SELECT STDDEV_SAMP(`s0`.`ratio value`) AS `c0` FROM" in (
        emit_compiled(root, ()).rendered.sql
    )


@pytest.mark.parametrize(
    "layer,code",
    (
        ("semantics", "COMPILED_SEMANTIC_AGGREGATE_ARGUMENT"),
        ("stage", "COMPILED_AGGREGATE_ARGUMENT"),
        ("emission", "COMPILED_EMISSION_AGGREGATE_ARGUMENT"),
    ),
)
def test_each_compiled_reader_refuses_a_renamed_statistic_on_its_own(
    tmp_path, monkeypatch, layer, code
):
    """With the cell check of every earlier compiled reader made to accept a
    grouped `max` bundle renamed `stddev`, the semantic verifier, the stage
    builder and the emission verifier each derive the cell from the records
    themselves and refuse it."""
    from pietto._project import project_completed_semantics as semantics
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project.project_compiled_schema import CompiledError

    root, forged = _renamed_statistic(
        tmp_path, "    group by key\n    select:\n        key\n        d = max(ratio)\n"
    )
    accept = lambda *args: forged  # noqa: E731
    if layer == "semantics":
        with monkeypatch.context() as patch:
            patch.setattr(semantics, "_spread_cell", accept)
            completed = semantics.derive_compiled_semantics(root, ())
        with pytest.raises(CompiledError, match=f"^{code}$"):
            semantics.verify_compiled_semantics(completed)
        return
    monkeypatch.setattr(semantics, "_spread_cell", accept)
    if layer == "emission":
        stage = grouping.build_compiled_stage

        def accepting_stage(*args):
            with monkeypatch.context() as inner:
                inner.setattr(grouping, "mysql_compiled_spread_cell", accept)
                return stage(*args)

        monkeypatch.setattr(grouping, "build_compiled_stage", accepting_stage)
    with pytest.raises(CompiledError, match=f"^{code}$"):
        emit_compiled(root, ())


@pytest.mark.parametrize("field", ("mode", "keys"))
def test_the_compiled_statistic_cell_needs_a_global_aggregate_without_keys(
    tmp_path, field
):
    """The compiled cell check reads the aggregate record's own mode and keys:
    the cell's records with only that stage made grouped, or keyed by the
    value's argument, leave the cell."""
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project.project_compiled_schema import FIELDS, Record

    root = build_compiled(
        _nullable_ratio(tmp_path, "    select:\n        d = stddev(ratio)\n").artifact
    ).root
    records = dict(root.records)
    entry = records[root.description.query]
    assert grouping.mysql_compiled_spread_cell(records, entry) is not None
    stage = records[records[entry.get("terminal")].get("input")]
    values = list(stage.values)
    values[FIELDS["aggregate"].index(field)] = (
        "grouped"
        if field == "mode"
        else records[stage.get("values")[0]].get("arguments")
    )
    records[stage.address] = Record(stage.address, tuple(values))
    assert grouping.mysql_compiled_spread_cell(records, entry) is None


@pytest.fixture(scope="module")
def inline_arguments_bundle(tmp_path_factory):
    """The PostgreSQL `inline_arguments` bundle, built once: each forgery
    below copies the records it changes and leaves the bundle as it is."""
    original = build(
        tmp_path_factory.mktemp("inline-arguments"),
        "postgres",
        "V_aggregate_blocked",
        "inline_arguments",
    )
    assert original.status == "VERIFIED" and original.artifact is not None
    return build_compiled(original.artifact)


@pytest.mark.parametrize("function", ("sum", "avg", "count"))
@pytest.mark.parametrize("forgery", ("literal", "constant_operation"))
def test_a_compiled_aggregate_that_reads_no_row_stays_refused(
    inline_arguments_bundle, function, forgery
):
    """A row expression argument opens on PostgreSQL; a forged argument that
    reads no row, the expression's own literal or that expression over its
    literal alone, stays refused."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Record,
        content_pin,
        encode,
    )

    built = inline_arguments_bundle
    (aggregate,) = (
        r
        for r in built.root.description.records
        if r.address.kind == "aggregate_value" and r.get("function") == function
    )
    (operation,) = aggregate.get("arguments")
    (literal,) = (
        operand
        for operand in built.root.records[operation].get("operands")
        if operand.kind == "literal"
    )
    record, field, value = (
        (aggregate, "arguments", (literal,))
        if forgery == "literal"
        else (built.root.records[operation], "operands", (literal, literal))
    )
    values = list(record.values)
    values[FIELDS[record.address.kind].index(field)] = value
    forged = Record(record.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (name, tuple(forged if r.address == forged.address else r for r in members))
            for name, members in built.root.description.members
        ),
    )
    raw = encode(description)
    root = load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_ARGUMENT$"):
        emit_compiled(root, ())


_CONDITIONAL_BODY = (
    "table result:\n    from rows\n    group by flag\n    select:\n"
    "        flag\n        n = sum(1 for o in group if o.id > 2)\n"
    '        s = sum(o.id for o in group if o.text == "a")\n'
)


@pytest.fixture(scope="module")
def conditional_original(tmp_path_factory):
    """The PostgreSQL conditional count and sum, built once: the replay and
    each forgery below read the artifact and leave it as it is."""
    item = emission.fixture("postgres", "T_row_direct", "table_preserve")
    source = item["source"].split("table result:", 1)[0] + _CONDITIONAL_BODY
    checked, original = emission.build_case(
        tmp_path_factory.mktemp("conditional"),
        source,
        item["contract"],
        item["policy"],
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    return original


def test_postgresql_conditional_count_and_sum_replay_from_compiled_input(
    conditional_original,
):
    """COUNT(CASE WHEN test THEN 1 END) and the COALESCE'd checked SUM of a
    conditional sum replay from compiled input with the sum's R13 evidence."""
    candidate = _compare(conditional_original.artifact, refinement=False)
    assert b"COUNT(CASE WHEN (" in candidate.rendered.sql
    assert b"COALESCE(CAST(SUM(CASE WHEN (" in candidate.rendered.sql
    assert [
        r.evidence for r in candidate.generated_requirements if r.kind == "aggregate"
    ] == [(), ("target_checked_signed64_narrowing",)]


@pytest.mark.parametrize(
    ("function", "forgery", "error"),
    (
        ("filtered_sum", "swapped", "COMPILED_AGGREGATE_SIGNATURE"),
        ("filtered_count", "int_test", "COMPILED_AGGREGATE_ARGUMENT"),
    ),
)
def test_a_compiled_conditional_aggregate_keeps_its_signature(
    conditional_original, function, forgery, error
):
    """A conditional sum reads one direct field, then its test; a conditional
    count's one argument is a Bool test: a forged bundle that breaks either is
    refused."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Record,
        content_pin,
        encode,
    )

    built = build_compiled(conditional_original.artifact)
    records = {
        r.get("function"): r
        for r in built.root.description.records
        if r.address.kind == "aggregate_value"
    }
    field, test = records["filtered_sum"].get("arguments")
    record = records[function]
    values = list(record.values)
    values[FIELDS[record.address.kind].index("arguments")] = (
        (test, field) if forgery == "swapped" else (field,)
    )
    forged = Record(record.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (name, tuple(forged if r.address == forged.address else r for r in members))
            for name, members in built.root.description.members
        ),
    )
    raw = encode(description)
    with pytest.raises(CompiledError, match=f"^{error}$"):
        emit_compiled(
            load_compiled(
                raw,
                expected_pin=content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            ),
            (),
        )


_GROUP_TEST_BODY = (
    "table result:\n    from rows\n    group by flag\n    select:\n"
    "        flag\n        a = all(o.id > 2 for o in group)\n"
    '        b = any(o.text == "a" for o in group)\n'
    "        s = sum(o.id for o in group if o.id > 2)\n"
)


@pytest.fixture(scope="module")
def group_test_original(tmp_path_factory):
    """The PostgreSQL `all` and `any` of a group, built once: the replay and
    each forgery below read the artifact and leave it as it is."""
    item = emission.fixture("postgres", "T_row_direct", "table_preserve")
    source = item["source"].split("table result:", 1)[0] + _GROUP_TEST_BODY
    checked, original = emission.build_case(
        tmp_path_factory.mktemp("group-test"),
        source,
        item["contract"],
        item["policy"],
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    return original


def test_postgresql_group_tests_replay_from_compiled_input(group_test_original):
    """`all` and `any` of a group, a count of the test compared with 0,
    replay from compiled input with no R13 evidence."""
    candidate = _compare(group_test_original.artifact, refinement=False)
    sql = candidate.rendered.sql
    assert b"(COUNT(CASE WHEN (" in sql
    assert b" THEN NULL ELSE 1 END) = 0)" in sql
    assert b" THEN 1 END) > 0)" in sql
    assert [
        r.evidence for r in candidate.generated_requirements if r.kind == "aggregate"
    ] == [(), (), ("target_checked_signed64_narrowing",)]


@pytest.mark.parametrize(
    ("function", "forgery", "error"),
    (
        ("group_any", "two", "COMPILED_AGGREGATE_SIGNATURE"),
        ("group_all", "int_test", "COMPILED_AGGREGATE_ARGUMENT"),
    ),
)
def test_a_compiled_group_test_keeps_its_signature(
    group_test_original, function, forgery, error
):
    """A test of the group reads one Bool test: a forged bundle with two
    arguments or an Int one is refused."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Record,
        content_pin,
        encode,
    )

    built = build_compiled(group_test_original.artifact)
    records = {
        r.get("function"): r
        for r in built.root.description.records
        if r.address.kind == "aggregate_value"
    }
    field, test = records["filtered_sum"].get("arguments")
    record = records[function]
    values = list(record.values)
    values[FIELDS[record.address.kind].index("arguments")] = (
        (field, test) if forgery == "two" else (field,)
    )
    forged = Record(record.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (name, tuple(forged if r.address == forged.address else r for r in members))
            for name, members in built.root.description.members
        ),
    )
    raw = encode(description)
    with pytest.raises(CompiledError, match=f"^{error}$"):
        emit_compiled(
            load_compiled(
                raw,
                expected_pin=content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            ),
            (),
        )


def test_postgresql_median_and_quantile_replay_from_compiled_input(tmp_path):
    """PERCENTILE_CONT, its float8 order cast, the fixed median fraction and
    the quantile's literal fraction replay from compiled input."""
    item = emission.fixture("postgres", "T_row_direct", "table_preserve")
    source = item["source"].split("table result:", 1)[0] + (
        "table result:\n    from rows\n    group by flag\n    select:\n"
        "        flag\n        middle = median(id)\n"
        "        high = quantile(id, 0.9)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    candidate = _compare(original.artifact, refinement=False)
    assert candidate.rendered.sql.count(b"PERCENTILE_CONT(") == 2
    assert b"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CAST(" in (
        candidate.rendered.sql
    )
    assert b"PERCENTILE_CONT(CAST('0.9' AS pg_catalog.float8))" in (
        candidate.rendered.sql
    )


@pytest.mark.parametrize("grouped", [True, False])
def test_postgresql_first_and_last_replay_from_compiled_input(tmp_path, grouped):
    """The ordered ARRAY_AGG element, `last`'s flipped directions and a result
    that may be None only without GROUP BY replay from compiled input."""
    item = emission.fixture("postgres", "T_row_direct", "table_preserve")
    keys = (
        "    group by flag\n    select:\n        flag\n"
        if grouped
        else ("    select:\n")
    )
    source = item["source"].split("table result:", 1)[0].replace(
        "    ratio: Float\n", "    ratio: Float\n    row_key = unique(id)\n", 1
    ) + (
        "table result:\n    from rows\n"
        + keys
        + "        f = first(text, order by ratio desc, id)\n"
        "        l = last(money, order by id)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    candidate = _compare(original.artifact, refinement=False)
    assert candidate.rendered.sql.count(b"(ARRAY_AGG(") == 2
    assert b'"s0"."order.id" DESC))[1]' in candidate.rendered.sql


def test_postgresql_quantile_over_join_rows_replays_from_compiled_input(tmp_path):
    """A quantile over LEFT JOIN rows keeps its literal fraction beside the
    joined argument in compiled input."""
    item = emission.fixture("postgres", "Z_aggregate_joined", "left_nullable")
    source = item["source"].split("query result:", 1)[0] + (
        "query result:\n    from keys\n    let r = agg\n"
        "    left join r on keys.rid == r.rid\n"
        "    group by:\n        keys.rid\n    select:\n        k = keys.rid\n"
        "        q = quantile(r.rid, 0.75)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    candidate = _compare(original.artifact, refinement=False)
    assert b"PERCENTILE_CONT(CAST('0.75' AS pg_catalog.float8))" in (
        candidate.rendered.sql
    )


@pytest.mark.parametrize(
    "arguments", ["keys.label, r.rid, r.label", "keys.label, lb, r.rid"]
)
def test_postgresql_count_distinct_tuple_over_join_rows_replays(tmp_path, arguments):
    """A distinct-tuple count over LEFT JOIN rows keeps each field's read, one
    from each input, a `let:` name of a field in any position included, in
    compiled input."""
    item = emission.fixture("postgres", "Z_aggregate_joined", "left_nullable")
    source = item["source"].split("query result:", 1)[0] + (
        "query result:\n    from keys\n    let r = agg\n"
        "    left join r on keys.rid == r.rid\n    let lb = r.label\n"
        "    group by:\n        keys.rid\n    select:\n        k = keys.rid\n"
        f"        d = count_distinct({arguments})\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    candidate = _compare(original.artifact, refinement=False)
    assert candidate.rendered.sql.count(b" IS NOT NULL THEN ROW(") == 1


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_uuid_order_replays_from_compiled_input(tmp_path, target):
    """Q3: a UUID comparison and window and result ORDER keys replay from
    compiled input and prepare as a live template."""
    checked, original = emission.temporal_case(
        tmp_path,
        target,
        "    from rows\n    where u < u or u <= u <= u\n    select:\n"
        "        key = u\n        r = row_number() window(order by u desc)\n"
        "    order by u\n",
    )
    assert checked.verified and original.status == "VERIFIED", original.blockers
    assert original.artifact is not None
    _compare(original.artifact, refinement=False)
    assert (
        prepare_live_template(original.artifact).artifact.rendered.sql
        == original.artifact.rendered.sql
    )
    # The R2 refinement page orders Int, Bool, Text and Decimal coordinates
    # only; it refuses a UUID key, as it refuses a Timestamp one.
    with pytest.raises(ValueError, match="^REFINEMENT_COMPARISON_DOMAIN$"):
        _compare_refinement(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "body",
    (
        "    from rows\n    group by id\n    select:\n        key = id\n"
        "        first = min(ts)\n        last = max(d2)\n",
        "    from rows\n    where id < 0\n    select:\n"
        "        first = min(ts2)\n        last = max(d)\n",
    ),
    ids=("grouped", "filtered_global"),
)
def test_temporal_extrema_replay_from_compiled_input(tmp_path, target, body):
    """MIN/MAX of a Timestamp and a Date replay from compiled input and
    prepare as a live template on both targets."""
    checked, original = emission.temporal_case(tmp_path, target, body)
    assert checked.verified and original.status == "VERIFIED", original.blockers
    assert original.artifact is not None
    _compare(original.artifact, refinement=False)
    assert (
        prepare_live_template(original.artifact).artifact.rendered.sql
        == original.artifact.rendered.sql
    )


@pytest.mark.parametrize(
    "target,variant",
    (
        ("postgres", "fo_ascending"),
        ("postgres", "fg_ratio"),
        ("postgres", "fd_rows"),
        ("postgres", "fi_all"),
        ("postgres", "fj_inner"),
        ("postgres", "fx_any"),
        ("postgres", "fc_rows"),
        ("mysql", "fc_rows"),
        ("mysql", "fc_where"),
        ("mysql", "fw_windows"),
        ("mysql", "fo_ascending"),
    ),
)
def test_float_equality_and_order_replay_from_compiled_input(tmp_path, target, variant):
    """Lane E: Float ORDER, GROUP BY, DISTINCT, INTERSECT, JOIN and correlated
    equalities and literal comparisons replay (MySQL Float ORDER too); R2
    refuses a Float coordinate, as it refuses a UUID one; the live template
    renders the same SQL."""
    original = build(tmp_path, target, emission.FLOAT_CASE, variant)
    assert original.status == "VERIFIED" and original.artifact is not None
    _compare(original.artifact, refinement=False)
    _live(original.artifact)
    if variant == "fo_ascending":
        with pytest.raises(ValueError, match="^REFINEMENT_COMPARISON_DOMAIN$"):
            _compare_refinement(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_compiled_float_equality_of_two_row_reads_is_refused_on_mysql(
    tmp_path, target, monkeypatch
):
    """Branch B on the compiled path: a record forged from `ratio < ratio` to
    `ratio == ratio` derives on PostgreSQL only; on MySQL derivation refuses it
    and the independent verifier refuses a derivation forged past that law."""
    from dataclasses import replace
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_completed_semantics import (
        derive_compiled_semantics,
        verify_compiled_semantics,
    )
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Record,
        content_pin,
        encode,
    )

    item = emission.fixture(target, "V_row_blocked", "float_comparison")
    source = item["source"].replace("same = ratio == ratio", "same = ratio < ratio")
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    built = build_compiled(original.artifact)
    (comparison,) = (
        r
        for r in built.root.description.records
        if r.address.kind == "operation" and r.get("operator") == ("comparison", "<")
    )
    values = list(comparison.values)
    values[FIELDS["operation"].index("operator")] = ("comparison", "==")
    forged = Record(comparison.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (name, tuple(forged if r.address == forged.address else r for r in members))
            for name, members in built.root.description.members
        ),
    )
    raw = encode(description)
    root = load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    if target == "postgres":
        verify_compiled_semantics(derive_compiled_semantics(root, ()))
        return
    with pytest.raises(CompiledError):
        derive_compiled_semantics(root, ())
    law = physical.resolved_comparison_realization
    with monkeypatch.context() as patch:
        patch.setattr(
            physical,
            "resolved_comparison_realization",
            lambda *args, operator, rows_both_sides, **_: law(
                *args, operator=operator, rows_both_sides=False
            ),
        )
        derived = derive_compiled_semantics(root, ())
    # The verifier's own comparison law raises its PIE-B1003 detail.
    with pytest.raises(ValueError, match="comparison_type_pair_not_admitted"):
        verify_compiled_semantics(derived)


@pytest.mark.parametrize(
    "body",
    (*(body for _, _, body in float_cells.QUALIFIED), *float_cells.SAME_CLASS.values()),
    ids=(
        *(
            " ".join((*cell, key or "")).strip()
            for cell, key, _ in float_cells.QUALIFIED
        ),
        *float_cells.SAME_CLASS,
    ),
)
def test_mysql_float_row_cells_replay_from_compiled_input(tmp_path, body):
    """Phase77 S06: compiled replay re-derives each qualified cell from the
    bundle's own records and renders the emitted SQL; so does the live
    template."""
    original = float_cells.build(tmp_path, "mysql", body)
    assert original.status == "VERIFIED" and original.artifact is not None
    _compare(original.artifact, refinement=False)
    _live(original.artifact)


def _float_cell_bundle(directory, body, monkeypatch):
    """A MySQL bundle built while emission admits every Float comparison of
    two row reads, as if its cell law were bypassed."""
    from pietto._project import project_sql_emission_rows as physical

    with monkeypatch.context() as patch:
        patch.setattr(
            physical,
            "mysql_float_cell",
            lambda request, expression: ("same_row", "select", "=="),
        )
        original = float_cells.build(directory, "mysql", body)
        assert original.status == "VERIFIED"
        return build_compiled(original.artifact)


def _loaded(built, description=None):
    from pietto._project.project_compiled_schema import content_pin, encode

    raw = built.payload if description is None else encode(description)
    return load_compiled(
        raw,
        expected_pin=built.pin if description is None else content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )


@pytest.mark.parametrize(
    "name",
    (
        *("same_field", "float_item", "key_first", "same_table", "semi_exists"),
        *("two_joins", "parameter_select"),
        *("same_value_same_field", "same_value_float_item"),
        *("join_same_side", "key_same_side", "mixed_key_widths"),
        *("non_null_operand", "nullable_key", "int_key", "key_width_255"),
        *("unselected_key_same_row", "unselected_wide_text"),
        *("unselected_nullable_float", "reordered_fields", "same_row_table_joined"),
        *("not_equal", "inner_not_equal"),
    ),
)
def test_a_compiled_mysql_float_comparison_outside_its_cell_is_refused(
    tmp_path, monkeypatch, name
):
    """A bundle whose emission bypassed the cell law: derivation re-derives
    the cell from the records and refuses it, and the independent verifier
    refuses a derivation forged past that law (a `same_value` call as its
    scalar-call domain, a comparison by the law's detail)."""
    from pietto._project import project_completed_semantics as semantics
    from pietto._project.project_compiled_schema import CompiledError

    built = _float_cell_bundle(tmp_path, float_cells.REFUSED[name][0], monkeypatch)
    root = _loaded(built)
    with pytest.raises(CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
        emit_compiled(root, ())
    with monkeypatch.context() as patch:
        patch.setattr(
            semantics,
            "_compiled_float_cell",
            lambda records, address: ("same_row", "select", "=="),
        )
        derived = semantics.derive_compiled_semantics(root, ())
    refusal = (
        (CompiledError, "^COMPILED_SEMANTIC_DOMAIN$")
        if name.startswith("same_value")
        else (ValueError, "comparison_type_pair_not_admitted")
    )
    with pytest.raises(refusal[0], match=refusal[1]):
        semantics.verify_compiled_semantics(derived)


def test_a_tampered_compiled_mysql_float_cell_is_refused(tmp_path, monkeypatch):
    """A qualified `not (f1 != f2)` bundle rewritten to `not (f1 == f2)`, which
    no cell holds: derivation refuses it, and the independent verifier
    refuses a derivation forged past the cell law."""
    from pietto._project import project_completed_semantics as semantics
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Record,
    )

    body = float_cells.query("from f6s", "select:", "    r = not (f1 != f2)")
    built = build_compiled(float_cells.build(tmp_path, "mysql", body).artifact)
    (comparison,) = (
        r
        for r in built.root.description.records
        if r.address.kind == "operation" and r.get("operator") == ("comparison", "!=")
    )
    values = list(comparison.values)
    values[FIELDS["operation"].index("operator")] = ("comparison", "==")
    forged = Record(comparison.address, tuple(values))
    root = _loaded(
        built,
        replace(
            built.root.description,
            members=tuple(
                (
                    name,
                    tuple(
                        forged if r.address == forged.address else r for r in members
                    ),
                )
                for name, members in built.root.description.members
            ),
        ),
    )
    with pytest.raises(CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
        semantics.derive_compiled_semantics(root, ())
    with monkeypatch.context() as patch:
        patch.setattr(
            semantics,
            "_compiled_float_cell",
            lambda records, address: ("same_row", "select", "not !="),
        )
        derived = semantics.derive_compiled_semantics(root, ())
    with pytest.raises(ValueError, match="comparison_type_pair_not_admitted"):
        semantics.verify_compiled_semantics(derived)


_KEY_CELL_FORMS = {**float_cells.KEY_FORMS, **float_cells.KEY_SAME_CLASS}


@pytest.mark.parametrize("name", sorted(_KEY_CELL_FORMS))
def test_mysql_float_key_cells_replay_from_compiled_input(tmp_path, name):
    """Phase77 S07: compiled replay re-derives each GROUP BY cell from the
    bundle's own records and renders the emitted SQL; so does the live
    template."""
    original = float_cells.build(tmp_path, "mysql", _KEY_CELL_FORMS[name][1])
    assert original.status == "VERIFIED" and original.artifact is not None
    _compare(original.artifact, refinement=False)
    _live(original.artifact)


@pytest.mark.parametrize(
    "name",
    (
        "group.fwf",
        "group_mixed_nullability",
        "group_where",
        "group_select_reordered",
        "group_upstream",
    ),
)
def test_a_compiled_mysql_float_key_outside_its_cell_is_refused(
    tmp_path, monkeypatch, name
):
    """A bundle whose emission bypassed the S07 cell law: compiled replay
    re-derives the cell from the records and refuses it, and the independent
    emission verifier refuses a replay whose derivation was forged past that
    law."""
    from pietto._project import project_completed_semantics as semantics
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_compiled_verification import (
        verify_compiled_emission,
    )

    _, built, _ = float_cells.forged_key_artifact(
        tmp_path, float_cells.KEY_REFUSED[name][0], monkeypatch
    )
    root = _loaded(built)
    with pytest.raises(CompiledError, match="^COMPILED_GROUP_KEY$"):
        emit_compiled(root, ())
    with monkeypatch.context() as patch:
        patch.setattr(
            semantics, "_compiled_float_key_cell", lambda records: ("group", ("H",))
        )
        candidate = emit_compiled(root, ())
    with pytest.raises(CompiledError, match="^COMPILED_EMISSION_GROUP_KEY$"):
        verify_compiled_emission(candidate, candidate.request)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_compiled_float_membership_of_two_row_reads_is_refused_on_mysql(
    tmp_path, target, monkeypatch
):
    """`ratio in (ratio, 1.0)`, its option an `==` of two row reads, emitted
    past the membership law, derives on PostgreSQL only; on MySQL derivation
    refuses it and the independent verifier refuses a derivation forged past
    that law."""
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_completed_semantics import (
        derive_compiled_semantics,
        verify_compiled_semantics,
    )
    from pietto._project.project_compiled_schema import CompiledError

    law = physical.resolved_membership_realization

    def admitted(*args, row_option_pair):
        return law(*args, row_option_pair=False)

    item = emission.fixture(target, "V_row_blocked", "float_comparison")
    source = item["source"].replace(
        "same = ratio == ratio", "same = ratio in (ratio, 1.0)"
    )
    with monkeypatch.context() as patch:
        patch.setattr(physical, "resolved_membership_realization", admitted)
        checked, original = emission.build_case(
            tmp_path, source, item["contract"], item["policy"]
        )
        built = build_compiled(original.artifact)
    assert checked.verified and original.status == "VERIFIED"
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    if target == "postgres":
        verify_compiled_semantics(derive_compiled_semantics(root, ()))
        return
    with pytest.raises(CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
        derive_compiled_semantics(root, ())
    with monkeypatch.context() as patch:
        patch.setattr(physical, "resolved_membership_realization", admitted)
        derived = derive_compiled_semantics(root, ())
    with pytest.raises(CompiledError, match="^COMPILED_SEMANTIC_DOMAIN$"):
        verify_compiled_semantics(derived)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "name",
    ("r01_c_kw_in", "r01_c_kw_nn_not_in", "select", "r01_u_let_in", "r01_u_src_not_in"),
)
def test_a_compiled_correlated_float_membership_is_refused_on_mysql(
    tmp_path, target, name, monkeypatch
):
    """R01: a class C form of the R01 cells, emitted as main (rows.AS_MAIN,
    which shuts emission's refusal), derives on PostgreSQL only; on MySQL
    derivation refuses it from the bundle's records and the independent
    verifier refuses a derivation forged past that check. The same read as
    a SELECT item, and a class U read, derive on both."""
    from pietto._project import project_completed_semantics as semantics
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_compiled_schema import CompiledError

    body = float_cells.R01_FORMS.get(name) or float_cells.query(
        "let m:",
        "    capture r01o",
        "    from r01i",
        "    where kw == r01o.kw",
        "    select:",
        "        v",
        "from r01o",
        "select:",
        "    id",
        "    f = v in m",
    )
    token = physical.AS_MAIN.set(True)
    try:
        outcome = float_cells.build(tmp_path, target, body)
        assert outcome.status == "VERIFIED" and outcome.artifact is not None
        with monkeypatch.context() as patch:
            patch.setattr(semantics, "_compiled_float_membership", lambda *a: False)
            built = build_compiled(outcome.artifact)
    finally:
        physical.AS_MAIN.reset(token)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    if target == "postgres" or name == "select" or "_u_" in name:
        semantics.verify_compiled_semantics(
            semantics.derive_compiled_semantics(root, ())
        )
        return
    with pytest.raises(CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
        semantics.derive_compiled_semantics(root, ())
    with monkeypatch.context() as patch:
        patch.setattr(semantics, "_compiled_float_membership", lambda *a: False)
        derived = semantics.derive_compiled_semantics(root, ())
    with pytest.raises(CompiledError, match="^COMPILED_SEMANTIC_DOMAIN$"):
        semantics.verify_compiled_semantics(derived)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("variant", ("let_key", "bind"))
def test_computed_let_determinant_replays_from_compiled_input(
    tmp_path, target, variant
):
    """A CASE determinant and MAX over a CASE LET value replay their own ports."""
    item = emission.fixture(target, "Y_aggregate_computed", variant)
    checked, original = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (6 if variant == "bind" else 0)
    # The R2 refinement page verifier does not read CASE yet (fails closed).
    _compare(original.artifact, refinement=False)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("bound", (False, True))
def test_computed_comparison_determinant_refines_from_compiled_input(
    tmp_path, target, bound
):
    """A comparison determinant and MAX over a LET value also keep the compiled
    refinement differential; the public R2 entry still refuses this shape."""
    item = emission.fixture(
        target, "Y_aggregate_satisfying", "bind" if bound else "retained"
    )
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "query result:\n    from agg\n    let big = value > 5\n"
        "    let level = 3\n    group by:\n        big\n    select:\n        big\n"
        "        total = count()\n        top = max(level)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (2 if bound else 0)
    _compare(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "value",
    (
        "1 if key > 1 else 0",
        "1 <= key <= 3",
        "key in (1, 2)",
        "Float(key)",
    ),
)
def test_row_let_operation_keeps_its_requirement_rules_on_replay(
    tmp_path, target, value
):
    """The compiled input attributes each retained demand as the source did."""
    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        f"query result:\n    from agg\n    let w = {value}\n"
        "    select:\n        w\n        rid\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    # The independent public consumer derives the source rules on its own.
    emission.decode_public(serialize_project_sql_emission(original))
    # The R2 refinement page verifier does not read these operations yet.
    _compare(original.artifact, refinement=False)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    (
        ("L_relation_exists", "kept"),
        ("L_relation_exists", "correlated"),
        ("L_relation_scalar", "kept"),
        ("L_relation_membership", "correlated"),
    ),
)
def test_block_read_keeps_its_requirement_rules_on_replay(
    tmp_path, target, case, variant
):
    """An `exists`, `scalar` or `in` read keeps its R11 demand in the compiled
    input, as the source attributes it (an `any` read: the named families)."""
    item = emission.fixture(target, case, variant)
    checked, original = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert "R11" in {r.rule for r in original.artifact.original_requirements}
    emission.decode_public(serialize_project_sql_emission(original))
    # R2 refines no `exists`, `scalar` or `in` read yet (fails closed).
    _compare(original.artifact, refinement=False)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("bound", (False, True))
@pytest.mark.parametrize(
    "tail", ("", "    having:\n        b\n    order by:\n        b desc\n")
)
def test_joined_computed_determinant_replays_from_compiled_input(
    tmp_path, target, bound, tail
):
    """S05j: compiled replay re-derives the two-sided determinant's risk law,
    MIN/MAX over the joined LET value and filtering/ordering by its output."""
    item = emission.fixture(
        target, "Y_aggregate_satisfying", "bind" if bound else "retained"
    )
    source = (
        emission.AGGREGATE_HEADER.format(target=target)
        + emission.AGGREGATE_COMPUTED_JOIN
        + tail
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (2 if bound else 0)
    _compare(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("bound", (False, True))
def test_joined_field_free_let_extrema_replay_from_compiled_input(
    tmp_path, target, bound
):
    """A12: MIN/MAX over a joined LET value that reads no field replay with no
    field dependency and the source's own linkage."""
    item = emission.fixture(
        target, "Y_aggregate_satisfying", "bind" if bound else "retained"
    )
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "query result:\n    from agg\n    let r = agg\n"
        "    inner join r on agg.key == r.key\n    let level = 3 * 2\n"
        "    group by:\n        agg.rid\n        r.rid\n    select:\n"
        "        rid = agg.rid\n        low = min(level)\n        top = max(level)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (2 if bound else 0)
    _compare(original.artifact)


_RIGHT_R = (
    "relationship link(many: Agg, one: Agg):\n    many.key == one.rid\n"
    "query result:\n    from agg\n    let r = agg\n"
    "    right join r on link(agg, r)\n"
)


def _right_case(tmp_path, target, body):
    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + _RIGHT_R + body
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    built = build_compiled(original.artifact)
    plan = emit_compiled(
        built.root, tuple(v.value for v in original.artifact.fixed_values)
    ).request.plan
    (evidence,) = plan.aggregate_evidence
    return original.artifact, built, evidence


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "body",
    (
        "    select:\n        n = count(agg.rid)\n",
        "    let p = agg\n    inner join p on link(p, agg)\n"
        "    select:\n        n = count(p.rid)\n",
    ),
    ids=("left_argument", "matched_input"),
)
def test_right_join_match_replays_only_for_aggregates_skipping_unmatched_rows(
    tmp_path, target, body
):
    """A RIGHT JOIN's at-most-one match gives no left-to-right grain dependency
    in the replay either, and an aggregate that never reads a right row that
    matches no left row (its argument is NULL there, or it reads an input
    matched from the left side) gets it back the same way: the replayed fan-out
    evidence equals the original and repeats no row."""

    artifact, built, evidence = _right_case(tmp_path, target, body)
    _compare(artifact, built=built)
    (right,) = (j for j in evidence.region.joins if j.record.get("kind") == "right")
    introduced = evidence.region.uses[right.record.get("inputs")[1]].ref
    assert not any(
        factor.introduction_use is introduced
        for dependency in right.properties.relational.grain.dependencies
        for factor in (*dependency.determinants, *dependency.dependents)
    )
    (linkage,) = evidence.grain_linkages
    assert linkage.closure.factors == evidence.region.final_properties.grain.active
    assert not linkage.multiplicity_exposures


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("nullable_key", (False, True))
def test_correlated_match_and_non_null_group_key_replay(tmp_path, target, nullable_key):
    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    header = emission.AGGREGATE_HEADER.format(target=target)
    body = _RIGHT_R
    if nullable_key:
        header = header.replace(
            "    agg_row = unique(rid)",
            "    agg_match = unique(key)\n    agg_row = unique(rid)",
        )
        body = body.removesuffix("\n") + " and r.flag\n"
    match = "link(p, r) and p.rid > 0"
    body += (
        "    let p = agg\n"
        + (
            f"    inner join p on {match}\n"
            if nullable_key
            else f"    where any({match} for p in p)\n"
        )
        + "    let x = agg\n    cross join x\n"
        "    group by agg.rid"
        + (", p.key" if nullable_key else "")
        + "\n    select:\n        n = count(x.rid)\n"
    )
    checked, original = emission.build_case(
        tmp_path, header + body, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    built = build_compiled(original.artifact)
    _compare(original.artifact, built=built)
    plan = emit_compiled(
        built.root, tuple(v.value for v in original.artifact.fixed_values)
    ).request.plan
    (evidence,) = plan.aggregate_evidence
    if nullable_key:
        from dataclasses import replace
        from pietto._project.project_compiled_schema import CompiledError
        from pietto._project.project_joined_aggregation import (
            verify_compiled_aggregate_evidence,
        )
        from pietto._project.project_row_keys import ProjectRowUniquenessStrength

        assert all(
            key.strength is ProjectRowUniquenessStrength.STRICT
            for protection in evidence.group_protections
            for key in protection.strict_keys
        )
        (protection,) = (
            protection
            for protection in evidence.group_protections
            if any(
                member.field_position == 0
                for value_class in protection.seed.classes
                for member in value_class.members
            )
        )
        assert not protection.protected_factors
        (nullable,) = (
            key
            for key in protection.input_properties.keys
            if key.strength is ProjectRowUniquenessStrength.LAX
        )
        forged = replace(protection, strict_keys=(*protection.strict_keys, nullable))
        supplied = (
            replace(
                evidence,
                group_protections=tuple(
                    forged if p is protection else p for p in evidence.group_protections
                ),
            ),
        )
        with pytest.raises(CompiledError, match="^COMPILED_GROUP_PROTECTION_KEYS$"):
            verify_compiled_aggregate_evidence(plan.ir, supplied)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("retained", (False, True), ids=("selected", "retained"))
@pytest.mark.parametrize(
    "variant",
    ("reordered", "duplicates", "wrong_pair", "missing_duplicate", "extra_on"),
)
def test_reordered_composite_reverse_match_replays_with_authored_order(
    tmp_path, monkeypatch, target, retained, variant
):
    from pietto._project import project_compiled_verification as verification
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
        compiled_orphan_free_dependencies,
        orphan_free_dependencies,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    forward = "many.key == one.rid and many.value == one.rid"
    reverse = "one.rid == many.value and one.rid == many.key"
    if variant in {"duplicates", "missing_duplicate"}:
        forward += " and many.key == one.rid"
    if variant == "duplicates":
        reverse += " and one.rid == many.key"
    elif variant == "wrong_pair":
        reverse = "one.rid == many.value and one.rid == many.rid"
    proved = variant in {"reordered", "duplicates"}
    extra_on = " and r.flag" if variant == "extra_on" else ""
    # Independent grouping keeps the negative controls valid without this proof.
    group = "agg.rid" if proved else "agg.rid, r.rid"
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        f"relationship forward_match(many: Agg, one: Agg):\n    {forward}\n"
        f"relationship reverse_match(one: Agg, many: Agg):\n    {reverse}\n"
        "query result:\n    from agg\n    let r = agg\n"
        f"    right join r on forward_match(agg, r){extra_on}\n"
        "    let p = agg\n    where any(reverse_match(r, p) for p in p)\n"
        f"    let x = agg\n    cross join x\n    group by {group}\n"
        "    select:\n        n = count(x.rid)\n"
    )
    logical = []
    if retained:
        # The request fixture needs a matching boundary; INNER TRUE keeps the product.
        source = (
            source.replace("query result:", "query unused:").replace(
                "cross join x", "inner join x on True"
            )
            + "query result:\n    from agg\n    select:\n        rid\n"
        )

        def witness(*args, **kwargs):
            return {**item, "source": source}

        monkeypatch.setattr(emission, "join_witness", witness)
        original = proof_artifact(tmp_path, retained=True)
        checker = verification.verify_logical_export

        def capture(description, checked, correspondence):
            checker(description, checked, correspondence)
            logical.append(checked.plan)

        monkeypatch.setattr(verification, "verify_logical_export", capture)
    else:
        checked, original = emission.build_case(
            tmp_path, source, item["contract"], item["policy"]
        )
        assert checked.verified
    assert original.status == "VERIFIED"
    artifact = original.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    if retained:
        loaded = load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
        replay = emit_compiled(loaded, tuple(v.value for v in artifact.fixed_values))
        assert replay.rendered.sql == artifact.rendered.sql
        assert len(replay.parameter_uses) == len(artifact.parameter_uses)
        (reference,) = logical
        assert not replay.request.plan.single_matches
        assert replay.request.plan.all_single_matches
        _compare_aggregate_evidence(reference, replay.request.plan)
    else:
        replay = _compare(artifact, built=built)
        reference = artifact.request.plan
    (source_aggregate,) = (
        a.authority.source
        for a in reference.aggregations
        if type(a.authority.source) is ProjectConcreteJoinedAggregation
    )
    (evidence,) = replay.request.plan.aggregate_evidence
    if retained:
        (source_request,) = (
            a
            for a in artifact.request.verification.completed.single_matches.entries
            if a.request.use.identity.join_position == 2
        )
        (compiled_request,) = (
            o.assessment
            for o in replay.request.plan.all_single_matches
            if o.request.use.get("boundaries")
            == (evidence.region.joins[-1].record.address,)
        )
        for assessment in (source_request, compiled_request):
            assert assessment.state.value == "legal_unproved"
            assert not assessment.proofs
            assert assessment.downstream_enforcement_required
    (source_occurrence,) = source_aggregate.aggregates
    (aggregate_address,) = evidence.stage.record.get("values")
    arguments = replay.request.plan.ir.completed.root.records[aggregate_address].get(
        "arguments"
    )
    old_dependencies = orphan_free_dependencies(source_occurrence)
    new_dependencies = compiled_orphan_free_dependencies(
        replay.request.plan.ir, evidence.region, evidence.stage, arguments
    )

    def signature(dependencies, grain):
        positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
        return tuple(
            (
                tuple(positions[f] for f in dependency.determinants),
                tuple(positions[f] for f in dependency.dependents),
            )
            for dependency in dependencies
        )

    source_region = source_aggregate.input_filter.joined_semantics.multifact_region
    expected = (((0,), (1,)),) if proved else ()
    assert (
        signature(old_dependencies, source_region.final_properties.relational.grain)
        == signature(new_dependencies, evidence.region.final_properties.grain)
        == expected
    )
    (linkage,) = evidence.grain_linkages
    assert linkage.closure.factors == evidence.region.final_properties.grain.active
    assert not linkage.multiplicity_exposures


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "where",
    (
        "x.rid is None",
        "r.rid > 5 and r.rid < 3",
        "agg.rid is not None or x.rid is None",
        "r.rid == 3",
    ),
    ids=("never_none", "contradiction", "vacuous_or", "key_held"),
)
def test_unmatched_row_value_proofs_replay_with_the_compiled_records(
    tmp_path, target, where
):
    """D-11: the compiled records give back the left-to-right dependency of a
    RIGHT JOIN whose unmatched rows the aggregate reads through values only
    (a never-None field tested `is None`, contradictory bounds, a vacuous
    `or`) or of one right row only (a key held to one value), as the written
    query does, so the replay finds no repeated rows either."""
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
        compiled_orphan_free_dependencies,
        orphan_free_dependencies,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "relationship forward_match(many: Agg, one: Agg):\n"
        "    many.key == one.rid\n"
        "query result:\n    from agg\n    let r = agg\n"
        "    right join r on forward_match(agg, r)\n    let x = agg\n"
        f"    cross join x\n    where {where}\n    group by agg.rid\n"
        "    select:\n        n = count(x.rid)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified
    assert original.status == "VERIFIED"
    artifact = original.artifact
    assert artifact is not None
    replay = _compare(artifact)
    reference = artifact.request.plan
    (source_aggregate,) = (
        a.authority.source
        for a in reference.aggregations
        if type(a.authority.source) is ProjectConcreteJoinedAggregation
    )
    (evidence,) = replay.request.plan.aggregate_evidence
    (source_occurrence,) = source_aggregate.aggregates
    (aggregate_address,) = evidence.stage.record.get("values")
    arguments = replay.request.plan.ir.completed.root.records[aggregate_address].get(
        "arguments"
    )

    def signature(dependencies, grain):
        positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
        return tuple(
            (
                tuple(positions[f] for f in dependency.determinants),
                tuple(positions[f] for f in dependency.dependents),
            )
            for dependency in dependencies
        )

    source_region = source_aggregate.input_filter.joined_semantics.multifact_region
    assert (
        signature(
            orphan_free_dependencies(source_occurrence),
            source_region.final_properties.relational.grain,
        )
        == signature(
            compiled_orphan_free_dependencies(
                replay.request.plan.ir, evidence.region, evidence.stage, arguments
            ),
            evidence.region.final_properties.grain,
        )
        == (((0,), (1,)),)
    )
    (linkage,) = evidence.grain_linkages
    assert not linkage.multiplicity_exposures


JOINED_AGGREGATE_HEADER = """shape Row:
    id: Int
    key: Int | None
    row_key = unique(id)
source lhs: Row = {target}.table("lhs")
source rhs: Row = {target}.table("rhs")
query per_key:
    from rhs
    group by:
        key
    select:
        key
        n = count()
"""
# The JOINs, WHERE and aggregates of `result` grouped by `lhs.key`.
JOINED_AGGREGATES = {
    "set_insensitive": (
        "    let r = rhs\n    left join r on r.key == lhs.key\n"
        "    let p = rhs\n    left join p on p.key == lhs.key\n",
        "top = max(r.id)\n        low = min(p.id)\n        n = count_distinct(r.key)",
    ),
    "left_many_side": (
        "    let r = rhs\n    left join r on r.key == lhs.id\n",
        "n = count(r.id)",
    ),
    "anti_join": (
        "    let r = rhs\n    left join r on r.key == lhs.key\n    where r.id is None\n",
        "n = count(lhs.id)",
    ),
    "grouped_key": (
        "    let g = per_key\n    left join g on g.key == lhs.id\n",
        "n = count(lhs.id)\n        m = count(g.n)",
    ),
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("name", JOINED_AGGREGATES)
def test_sound_joined_aggregates_replay_and_bind_their_live_template(
    tmp_path, target, name
):
    """D-11 and B14: MIN, MAX and COUNT DISTINCT over JOINs that repeat rows,
    a count of a LEFT JOIN's many side, an anti-join through a never-None
    field and a JOIN on every GROUP BY key of a grouped query build, load and
    replay from compiled input, and their live template renders the emitted
    SQL."""
    joins, aggregates = JOINED_AGGREGATES[name]
    item = emission.join_witness(
        target,
        {
            "main.pietto": JOINED_AGGREGATE_HEADER.format(target=target)
            + "query result:\n    from lhs\n"
            + joins
            + "    group by lhs.key\n    select:\n        k = lhs.key\n"
            + f"        {aggregates}\n"
        },
    )
    _, original = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert original.status == "VERIFIED", original.blockers
    assert original.artifact is not None
    sql = original.artifact.rendered.sql
    assert b" LEFT JOIN " in sql and b" GROUP BY " in sql
    if name == "grouped_key":
        # A compiled JOIN also reads a grouped input's GROUP BY key as a key
        # its `on` matches, which the live `on` proof does not reach (0.1.8
        # already replays more keys, FDs and grain for a plain JOIN on such a
        # key). Here the replayed grain gains the dependency lhs -> g, and the
        # aggregate evidence's common grain gains the candidate lhs and turns
        # ambiguous instead of unique, so only the SQL is compared.
        built = build_compiled(original.artifact)
        loaded = load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
        assert emit_compiled(loaded, ()).rendered.sql == sql
    else:
        _compare(original.artifact)
    _live(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_joined_single_read_computed_key_replays_as_computed(tmp_path, target):
    """`r.rid + 0` reads one field through an operation: replay keeps it a
    computed key recorded on the right side, never a direct key seeding that
    side's class, and forged records are refused."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_joined_aggregation import (
        verify_compiled_aggregate_evidence,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "query result:\n    from agg\n    let r = agg\n"
        "    inner join r on agg.key == r.key\n    let k = r.rid + 0\n"
        "    group by:\n        k\n        agg.rid\n    select:\n        k\n"
        "        rid = agg.rid\n        total = count()\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    _compare(original.artifact)
    plan = emit_compiled(
        build_compiled(original.artifact).root,
        tuple(v.value for v in original.artifact.fixed_values),
    ).request.plan
    (evidence,) = plan.aggregate_evidence
    right, left = evidence.group_protections
    assert right.group_keys == () and len(right.computed_keys) == 1
    assert len(left.group_keys) == 1 and left.computed_keys == ()
    assert not right.protected_factors and left.protected_factors
    for forged in (
        (replace(right, group_keys=right.computed_keys, computed_keys=()), left),
        (
            replace(right, computed_keys=()),
            replace(left, computed_keys=right.computed_keys),
        ),
    ):
        with pytest.raises(CompiledError, match="^COMPILED_GROUP_PROTECTION_ROOT$"):
            verify_compiled_aggregate_evidence(
                plan.ir, (replace(evidence, group_protections=forged),)
            )
    (linkage,) = evidence.grain_linkages
    assert linkage.computed_key_factors
    assert linkage.computed_key_factors != linkage.group_protection_factors
    for factors in ((), linkage.group_protection_factors):
        with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_LINKAGE_ROOT$"):
            verify_compiled_aggregate_evidence(
                plan.ir,
                (
                    replace(
                        evidence,
                        grain_linkages=(
                            replace(linkage, computed_key_factors=factors),
                        ),
                    ),
                ),
            )


def _compare(artifact, *, refinement=True, built: CompiledBuild | None = None):
    assert artifact is not None
    reference = prepare_output(artifact)
    if built is None:
        built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(v.value for v in artifact.fixed_values)
    candidate = emit_compiled(loaded, values)
    observed = prepare_output(candidate)
    assert candidate.rendered.sql == artifact.rendered.sql
    assert tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.nullable,
            c.realization.domain,
        )
        for c in observed.columns
    ) == tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.nullable,
            c.realization.domain,
        )
        for c in reference.columns
    )
    assert tuple(
        (
            f.ordinal,
            f.label,
            f.shape.canonical.name,
            f.shape.canonical.kind,
            f.nullability.value,
            None if f.meaning is None else f.meaning.law,
        )
        for f in observed.contract.shape.fields
    ) == tuple(
        (
            f.ordinal,
            f.label,
            f.shape.canonical.name,
            f.shape.canonical.kind,
            f.nullability.value,
            None if f.meaning is None else f.meaning.law,
        )
        for f in reference.contract.shape.fields
    )
    from pietto._project.project_query_block_ir_verification import (
        _class_signatures,
        _actual_key_signatures,
        _actual_fd_signatures,
    )

    original_properties = next(
        d.entry.active_properties.relational
        for d in artifact.request.plan.bindings.definitions
        if d.entry.owner is artifact.request.verification.selected_owner
    )
    loaded_properties = candidate.request.plan.ir.selected.properties.relational
    for signature in (_class_signatures, _actual_key_signatures, _actual_fd_signatures):
        assert signature(loaded_properties) == signature(original_properties)

    def grain_signature(grain):
        positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
        return (
            grain.state.value,
            tuple(f.identity.kind.value for f in grain.factors),
            tuple(positions[f] for f in grain.active),
            tuple(
                (
                    tuple(positions[f] for f in d.determinants),
                    tuple(positions[f] for f in d.dependents),
                )
                for d in grain.dependencies
            ),
        )

    assert grain_signature(loaded_properties.grain) == grain_signature(
        original_properties.grain
    )
    _compare_requirements(artifact, candidate)
    _compare_aggregate_evidence(artifact.request.plan, candidate.request.plan)
    if refinement:
        _compare_refinement(artifact)
    assert len(candidate.parameter_uses) == len(artifact.parameter_uses)
    assert all(
        new is not old
        for new, old in zip(
            candidate.request.sources, artifact.request.sources, strict=True
        )
    )
    return candidate


def _live(artifact):
    """The live template renders the emitted SQL, and binding the emitted
    literal values renders it again and sends the emission's arguments."""
    from pietto._project.project_execution_binding_verification import (
        native_arguments,
    )

    template = prepare_live_template(artifact)
    assert template.artifact.rendered.sql == artifact.rendered.sql
    values = tuple(v.value for v in artifact.fixed_values)
    bound = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    assert bound.artifact.rendered.sql == artifact.rendered.sql
    assert bound.arguments == native_arguments(artifact, values)
    return bound


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_original_maximum_static_limit_round_trip(tmp_path, target):
    import _pietto_sql_emission as emission
    from pietto.semantic.relation_limits import MAX_RELATION_LIMIT

    fixture = emission.fixture(target, "O_result_limit", "zero")
    source = fixture["source"]
    assert "limit 0" in source
    source = source.replace("limit 0", "limit " + str(MAX_RELATION_LIMIT))
    checked, outcome = emission.build_case(
        tmp_path, source, fixture["contract"], "preserve_literals"
    )
    assert checked.verified and outcome.status == "VERIFIED"
    _compare(outcome.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "precision,state", [(p, s) for p in (39, 65) for s in ("values", "empty", "null")]
)
def test_original_seven_scalar_templates(tmp_path, target, precision, state):
    from _pietto_execution_rows_cases import seven_artifact

    original = seven_artifact(
        tmp_path / "seven-build", target, precision=precision, state=state
    )
    _compare(original)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,left_key,right_key,kind,match,expected",
    (
        ("forward", False, True, "inner", "call", (((0,), (1,)),)),
        ("reverse", True, False, "inner", "call", (((1,), (0,)),)),
        ("both", True, True, "inner", "call", (((0,), (1,)), ((1,), (0,)))),
        ("swapped", True, True, "inner", "swapped", (((0,), (1,)), ((1,), (0,)))),
        ("left", True, True, "left", "call", (((0,), (1,)),)),
        ("right", True, True, "right", "call", (((1,), (0,)),)),
        # Hand-written ON equalities prove what the call proves.
        (
            "handwritten",
            True,
            True,
            "inner",
            "handwritten",
            (((0,), (1,)), ((1,), (0,))),
        ),
        ("nonmandatory", True, True, "inner", "or", ()),
        ("same_side", True, True, "inner", "same_side", ()),
        (
            "chain",
            True,
            True,
            "inner",
            "call",
            (((0,), (1,)), ((1,), (0,)), ((0, 1), (2,)), ((2,), (0, 1))),
        ),
    ),
    ids=(
        "forward",
        "reverse",
        "both",
        "swapped",
        "left",
        "right",
        "handwritten",
        "nonmandatory",
        "same_side",
        "chain",
    ),
)
def test_compiled_predicate_keys_preserve_complete_grain_dependencies(
    tmp_path, target, case, left_key, right_key, kind, match, expected
):
    from dataclasses import replace
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_grain import ProjectGrainDependencyFact
    from pietto._project.project_query_block_ir import build_compiled_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_compiled_join_grain,
    )

    key = "    row_id = unique(id)\n"
    equality = (
        "r.id == l.id and r.key == l.key"
        if match == "swapped"
        else "l.id == r.id and l.key == r.key"
    )
    predicate = (
        "lhs.id == r.id and lhs.key == r.key"
        if match == "handwritten"
        else "Link(lhs, r) or True"
        if match == "or"
        else "LeftOnly(lhs) and r.id > 0"
        if match == "same_side"
        else "Link(lhs, r)"
    )
    later = (
        "    let again = rhs\n    inner join again on Link(lhs, again)\n"
        if case == "chain"
        else ""
    )
    source = f"""shape LeftRow:
    id: Int
    key: Int | None
{key if left_key else ""}shape RightRow:
    id: Int
    key: Int | None
{key if right_key else ""}source lhs: LeftRow = {target}.table("lhs")
source rhs: RightRow = {target}.table("rhs")
relationship Link(l: LeftRow, r: RightRow):
    {equality}
relationship LeftOnly(l: LeftRow):
    l.id == l.id
query result:
    from lhs
    let r = rhs
    {kind} join r on {predicate}
{later}    select:
        left_id = lhs.id
        right_key = r.key
"""
    fixture = emission.join_witness(target, "")
    verified, outcome = emission.build_case(
        tmp_path / case, source, fixture["contract"]
    )
    assert verified.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, ())
    assert replay.rendered.sql == outcome.artifact.rendered.sql
    ir = replay.request.plan.ir
    joins = tuple(operator for operator in ir.operators if operator.kind == "join")
    operator = joins[-1]
    properties = operator.properties.relational
    grain = properties.grain
    positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
    observed = tuple(
        (
            tuple(positions[f] for f in d.determinants),
            tuple(positions[f] for f in d.dependents),
        )
        for d in grain.dependencies
    )
    assert observed == expected
    assert operator.record.get("equalities") == ()
    parents = {item.record.address: item for item in ir.operators}
    verify_compiled_join_grain(ir, operator, parents)
    extra = ProjectGrainDependencyFact(
        determinants=(grain.active[0],), dependents=(grain.active[-1],)
    )
    damages = [(*grain.dependencies, extra)]
    if grain.dependencies:
        first = grain.dependencies[0]
        damages.extend(
            (
                grain.dependencies[1:],
                (*grain.dependencies, first),
                (
                    replace(
                        first,
                        determinants=first.dependents,
                        dependents=first.determinants,
                    ),
                    *grain.dependencies[1:],
                ),
            )
        )
        foreign = build_compiled_query_block_ir(ir.completed)
        foreign_operator = next(
            item
            for item in foreign.operators
            if item.record.address == operator.record.address
        )
        foreign_first = foreign_operator.properties.relational.grain.dependencies[0]
        damages.append((foreign_first, *grain.dependencies[1:]))
    if len(grain.dependencies) > 1:
        damages.append(tuple(reversed(grain.dependencies)))
    for dependencies in damages:
        forged = replace(
            operator,
            properties=replace(
                operator.properties,
                relational=replace(
                    properties, grain=replace(grain, dependencies=dependencies)
                ),
            ),
        )
        with pytest.raises(
            CompiledError, match="^COMPILED_PROPERTY_JOIN_DEPENDENCIES$"
        ):
            verify_compiled_join_grain(ir, forged, parents)


@pytest.mark.parametrize(
    "target,case,kind,predicate,local_factors",
    [
        pytest.param(target, case, kind, predicate, factors, id=f"{target}-{case}")
        for target in ("postgres", "mysql")
        for case, kind, predicate, factors in (
            ("inner", "inner", "Many(dimension, signal)", (1,)),
            ("right", "right", "Many(dimension, signal)", (1,)),
            ("left", "left", "Many(dimension, signal)", ()),
            ("full", "full", "Many(dimension, signal)", ()),
            ("or", "inner", "Many(dimension, signal) or True", ()),
            ("not", "inner", "not Many(dimension, signal)", ()),
            ("missing_composite", "inner", "Partial(dimension, signal)", ()),
            (
                "multiple_bindings",
                "inner",
                "Many(dimension, signal) and Many(agg, signal)",
                (0, 1),
            ),
        )
        if target == "postgres" or kind != "full"
    ],
)
def test_compiled_local_key_grain_does_not_bound_accumulated_left(
    tmp_path, target, case, kind, predicate, local_factors
):
    """An event-expanded left row keeps each independently proved local edge."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
    from pietto._project.project_grain import (
        CompiledGrainFactorIdentity,
        ProjectGrainDependencyFact,
        ProjectJoinGrainFactorIdentity,
    )
    from pietto._project.project_query_block_ir_verification import (
        verify_compiled_join_grain,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    header = emission.AGGREGATE_HEADER.format(target=target)
    composite = case == "missing_composite"
    suffix = " and a.label == b.label" if composite else ""
    if composite:
        header = header.replace("unique(rid)", "unique(rid, label)")
    source = header + (
        f"relationship Same(a: Agg, b: Agg):\n    a.rid == b.rid{suffix}\n"
        f"relationship Many(a: Agg, b: Agg):\n    a.rid == b.key{suffix}\n"
        "relationship Partial(a: Agg, b: Agg):\n    a.rid == b.key\n"
        "query result:\n    from agg\n    let dimension = agg\n"
        "    inner join dimension on Same(agg, dimension)\n"
        "    let event = agg\n    inner join event on Many(agg, event)\n"
        f"    let signal = agg\n    {kind} join signal on {predicate}\n"
        "    select:\n        account_id = agg.rid\n"
        "        dimension_id = dimension.rid\n        event_id = event.rid\n"
        "        signal_id = signal.rid\n"
    )
    checked, outcome = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    replay = _compare(artifact, refinement=False)
    (region,) = (
        artifact.request.verification.completed.effective_outputs.current_regions
    )
    original = region.joins[-1]
    assert isinstance(original, ProjectCurrentBinaryJoin)
    ir = replay.request.plan.ir
    joins = tuple(item for item in ir.operators if item.kind == "join")
    operator = joins[-1]
    properties = operator.properties.relational
    grain = properties.grain
    parents = {item.record.address: item for item in ir.operators}
    left_use = ir.completed.root.records[operator.record.get("inputs")[0]]
    left = parents[left_use.get("producer")].properties.relational
    expected = (
        ((0,), (1,)),
        ((1,), (0,)),
        ((2,), (0, 1)),
        *(((3,), (factor,)) for factor in local_factors),
    )
    columns = tuple(name for name, _ in emission.AGGREGATE_COLUMNS)
    key = tuple(
        i
        for i, name in enumerate(columns)
        if name == "rid" or composite and name == "label"
    )
    event_key = tuple(2 * len(columns) + i for i in key)
    signal_key = tuple(3 * len(columns) + i for i in key)
    for incoming, current, node, introductions in (
        (
            original.left_input,
            original.properties.relational,
            original.node.ref,
            (
                region.joins[0].input_uses[0].ref,
                *(join.input_uses[1].ref for join in region.joins),
            ),
        ),
        (
            left,
            properties,
            operator.ref,
            (
                ir.references[joins[0].record.get("inputs")[0]],
                *(ir.references[j.record.get("inputs")[1]] for j in joins),
            ),
        ),
    ):
        # The only accumulated key belongs to event, not the matched dimension.
        for value, positions in (
            (incoming, event_key),
            (current, (*event_key, *signal_key)),
        ):
            assert tuple(
                tuple(m.field_position for c in k.determinants for m in c.members)
                for k in value.keys
            ) == (positions,)
        current_grain = current.grain
        positions = {f.identity: i for i, f in enumerate(current_grain.factors)}
        assert (
            tuple(
                (
                    tuple(positions[f] for f in d.determinants),
                    tuple(positions[f] for f in d.dependents),
                )
                for d in current_grain.dependencies
            )
            == expected
        )
        identities = tuple(
            f.identity
            for f in current_grain.factors
            if isinstance(
                f.identity,
                (ProjectJoinGrainFactorIdentity, CompiledGrainFactorIdentity),
            )
        )
        assert len(identities) == len(current_grain.factors)
        assert len({f.base for f in identities}) == 1
        assert len({f.introduction_use for f in identities}) == 4
        assert tuple(positions[f] for f in current_grain.active) == (0, 1, 2, 3)
        for factor, use in zip(current_grain.active, introductions, strict=True):
            assert isinstance(
                factor, (ProjectJoinGrainFactorIdentity, CompiledGrainFactorIdentity)
            )
            assert factor.introduction_use is use
            assert factor.kind.value == "source_domain"
        left_nulling = (node,) if kind in {"right", "full"} else ()
        right_nulling = (node,) if kind in {"left", "full"} else ()
        assert tuple(f.nulling_joins for f in identities) == (
            left_nulling,
            left_nulling,
            left_nulling,
            right_nulling,
        )
    verify_compiled_join_grain(ir, operator, parents)
    # A local match cannot determine the unmatched event or the whole left row.
    damages = []
    for dependents in ((grain.active[2],), grain.active[:3]):
        extra = ProjectGrainDependencyFact(
            determinants=(grain.active[3],), dependents=dependents
        )
        damages.append((*grain.dependencies, extra))
    if case == "multiple_bindings":
        prefix = grain.dependencies[:-2]
        account, dimension = grain.dependencies[-2:]
        damages.extend(
            (
                (*prefix, dimension),
                (*prefix, account),
                (*prefix, dimension, account),
            )
        )
    for dependencies in damages:
        forged = replace(
            operator,
            properties=replace(
                operator.properties,
                relational=replace(
                    properties,
                    grain=replace(grain, dependencies=dependencies),
                ),
            ),
        )
        with pytest.raises(
            CompiledError, match="^COMPILED_PROPERTY_JOIN_DEPENDENCIES$"
        ):
            verify_compiled_join_grain(ir, forged, parents)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("right_unique", (False, True))
def test_original_relationship_property_laws(tmp_path, target, right_unique):
    from _pietto_execution_guard_cases import planned, DIRECT
    from pietto._project.project_sql_emission import emit_project_sql

    body = DIRECT.replace("        on lhs.id == r.id\n", "        via link: l -> r\n")
    verified, contract = planned(
        tmp_path / "relationship",
        target,
        body,
        requested=False,
        link=True,
        right_unique=right_unique,
    )
    outcome = emit_project_sql(verified, contract)
    assert outcome.status == "VERIFIED"
    _compare(outcome.artifact)


@pytest.mark.parametrize(
    "target,case",
    [
        (target, case)
        for target in ("postgres", "mysql")
        for case in manifest()
        if target == "postgres" or not case["options"].get("postgres_only", False)
    ],
    ids=lambda value: value["name"] if isinstance(value, dict) else value,
)
def test_original_guard_preparation_closure(tmp_path, target, case):
    from pietto._project.project_guard_preparation import (
        prepare_compiled_guarded,
        prepare_guarded_template,
    )
    from pietto._project.project_guard_program import (
        prepare_program,
        pure_static_proofs,
    )
    from pietto._project.project_execution_template import bind_values

    original = case_preparation(tmp_path / "guard-source", target, case)
    source_refinement = None
    if case["options"].get("refined", False):
        from pietto._project.project_guard_preparation import prepare_guarded_output
        from pietto._project.project_refinement import prepare_refinement, TieRefinement

        source_refinement = prepare_refinement(
            original.artifact,
            capabilities(original.artifact),
            policy=TieRefinement(),
            output=prepare_guarded_output(original),
        )
    built = build_compiled(
        original.artifact, guarded=original, refinement=source_refinement
    )
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    artifact = emit_compiled(
        root, tuple(v.value for v in original.artifact.fixed_values)
    )
    candidate = prepare_compiled_guarded(artifact)
    reference, observed = prepare_program(original), prepare_program(candidate)
    assert artifact.rendered.sql == original.artifact.rendered.sql
    assert len(observed.subjects) == len(reference.subjects)
    assert tuple(
        len(pure_static_proofs(observed, s)) for s in observed.subjects
    ) == tuple(len(pure_static_proofs(reference, s)) for s in reference.subjects)
    assert tuple(
        (o.request.scope.value, o.assessment.state.value, len(o.proofs), len(o.joins))
        for o in candidate.scope.obligations
    ) == tuple(
        (o.request.scope.value, o.assessment.state.value, len(o.proofs), len(o.joins))
        for o in original.scope.obligations
    )
    template = prepare_guarded_template(candidate)
    values = tuple(v.value for v in original.artifact.fixed_values)
    rebound = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    assert rebound.guarded is not None
    assert rebound.artifact.rendered.sql == artifact.rendered.sql
    assert len(prepare_program(rebound.guarded, binding=rebound).subjects) == len(
        reference.subjects
    )
    from pietto._project.project_guard_program import statement_for
    from pietto._project.project_guard_rendering import render_guard
    from pietto._project.project_guard_verification import verify_native_guard

    if source_refinement is not None:
        from pietto._project.project_refinement import prepare_compiled_refinement

        refined = prepare_compiled_refinement(
            rebound.artifact, binding=rebound, guarded=rebound.guarded
        )
        _compare_refined_structure(source_refinement, refined)
        observed = prepare_program(rebound.guarded, binding=rebound, refinement=refined)
    if any(not pure_static_proofs(observed, subject) for subject in observed.subjects):
        native = render_guard(statement_for(observed, "guard"))
        verify_native_guard(native)


def test_compiled_requirement_correspondence_rejects_coordinated_damage(tmp_path):
    from dataclasses import replace
    from types import MappingProxyType
    from _pietto_execution_postgres_rows_probe import template
    from pietto._project.project_sql_plan_requirements import (
        verify_compiled_requirement_report,
        build_project_sql_requirement_report,
    )
    from pietto._project.project_compiled_verification import verify_compiled_emission

    source = template(tmp_path / "requirements-source")
    built = build_compiled(source.artifact)
    artifact = emit_compiled(
        built.root, tuple(v.value for v in source.artifact.fixed_values)
    )
    report = artifact.request.report
    assert artifact.original_requirements and artifact.generated_requirements
    assert (
        verify_compiled_requirement_report(report, artifact.request.verification)
        is report
    )
    with pytest.raises(
        ValueError,
        match=r"^Requirement report construction requires complete current plan evidence\.$",
    ):
        build_project_sql_requirement_report(artifact.request.verification)
    damaged = (
        replace(report, entries=()),
        replace(report, entries=report.entries[::-1]),
        replace(report, entries=(*report.entries, report.entries[-1])),
        replace(
            report,
            entries=(),
            links=(),
            by_family=MappingProxyType({}),
            by_subject=MappingProxyType({}),
            by_definition=MappingProxyType({}),
            by_stage=MappingProxyType({}),
            by_input_use=MappingProxyType({}),
            proved=(),
            enforcement_required=(),
        ),
        replace(
            report,
            entries=(
                replace(report.entries[0], origin=report.entries[-1].origin),
                *report.entries[1:],
            ),
        ),
    )
    codes = ("INVENTORY", "ENTRY", "INVENTORY", "INVENTORY", "ENTRY")
    for candidate, code in zip(damaged, codes, strict=True):
        with pytest.raises(ValueError, match="^COMPILED_REQUIREMENT_%s$" % code):
            verify_compiled_requirement_report(candidate, artifact.request.verification)
    for candidate, code in (
        (replace(artifact, original_requirements=()), "ORIGINAL"),
        (replace(artifact, generated_requirements=()), "GENERATED"),
        (
            replace(
                artifact, generated_requirements=artifact.generated_requirements[::-1]
            ),
            "GENERATED",
        ),
    ):
        with pytest.raises(
            ValueError, match="^COMPILED_EMISSION_%s_REQUIREMENTS$" % code
        ):
            verify_compiled_emission(candidate, artifact.request)


def _compare_aggregate_evidence(source, candidate):
    from dataclasses import replace
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
    )
    from pietto._project.project_sql_plan_verification import verify_compiled_sql_plan

    original = tuple(
        a.authority.source
        for a in source.aggregations
        if type(a.authority.source) is ProjectConcreteJoinedAggregation
    )
    assert len(candidate.aggregate_evidence) == len(original)
    assert len(candidate.aggregate_risks) == len(source.aggregate_risks)
    for observed, expected in zip(candidate.aggregate_evidence, original, strict=True):
        old_region = expected.input_filter.joined_semantics.multifact_region
        new_region = observed.region
        old_grain = old_region.final_properties.relational.grain
        new_grain = new_region.final_properties.grain
        old_factors = {f.identity: i for i, f in enumerate(old_grain.factors)}
        new_factors = {f.identity: i for i, f in enumerate(new_grain.factors)}
        old_uses = {
            use.ref: (i, j)
            for i, join in enumerate(old_region.region.joins)
            for j, use in enumerate(join.input_uses)
        }
        new_uses = {
            candidate.references[a]: (i, j)
            for i, join in enumerate(new_region.joins)
            for j, a in enumerate(join.record.get("inputs"))
        }
        assert tuple(f.kind.value for f in old_grain.active) == tuple(
            f.kind.value for f in new_grain.active
        )

        def classes(values):
            return tuple(tuple(f.field_position for f in c.members) for c in values)

        new_keys = {
            candidate.references[a]: i
            for i, a in enumerate(observed.stage.record.get("keys"))
        }

        def protection(value, factors, uses, ordinal):
            return (
                uses[value.introduction_use.ref],
                len(value.group_keys),
                tuple(ordinal(k) for k in value.computed_keys),
                classes(value.seed.classes),
                tuple(
                    (classes(k.determinants), k.strength.value, len(k.supports))
                    for k in value.strict_keys
                ),
                tuple(
                    (
                        d.status.value,
                        classes(d.seed.classes),
                        classes(d.requested.classes),
                        classes(d.closure.classes.classes),
                        tuple(classes(step.derived) for step in d.closure.witness),
                    )
                    for d in value.determinations
                ),
                tuple(factors[f] for f in value.protected_factors),
            )

        assert tuple(
            protection(p, new_factors, new_uses, new_keys.__getitem__)
            for p in observed.group_protections
        ) == tuple(
            protection(p, old_factors, old_uses, lambda k: k.source_ordinal)
            for p in expected.group_protections
        )

        def direction(value, factors):
            return (
                value.status.value,
                tuple(factors[f] for f in value.seed.factors),
                tuple(factors[f] for f in value.requested.factors),
                tuple(factors[f] for f in value.closure.factors),
            )

        def comparison(value, factors):
            return (
                value.status.value,
                direction(value.left_to_right, factors),
                direction(value.right_to_left, factors),
            )

        def linkage(value, factors):
            return (
                tuple(factors[f] for f in value.argument_factors),
                tuple(factors[f] for f in value.group_protection_factors),
                tuple(factors[f] for f in value.computed_key_factors),
                tuple(factors[f] for f in value.combined_seed.factors),
                tuple(factors[f] for f in value.closure.factors),
                value.contextual_grain.state.value,
                comparison(value.final_comparison, factors),
                tuple(
                    tuple(factors[f] for f in e.factor_additions)
                    for e in value.multiplicity_exposures
                ),
                tuple(r.value for r in value.multiplicity_risks),
                tuple(r.value for r in value.requirements),
            )

        assert tuple(linkage(v, new_factors) for v in observed.grain_linkages) == tuple(
            linkage(v, old_factors) for v in expected.grain_linkages
        )
        assert tuple(
            (
                v.function,
                len(v.arguments),
                tuple(
                    (new_uses[d.introduction_use.ref], d.input_field.field_position)
                    for d in v.field_dependencies
                ),
            )
            for v in observed.aggregates
        ) == tuple(
            (
                # Compiled input names a distinct-tuple count by its identity.
                "count_distinct_tuple"
                if v.function_name == "count_distinct" and len(v.call.arguments) > 1
                else v.function_name,
                len(v.call.arguments),
                tuple(
                    (
                        old_uses[d.field_semantics.introduction_use.ref],
                        d.field_semantics.input_field.field_position,
                    )
                    for d in v.field_dependencies
                ),
            )
            for v in expected.aggregates
        )

        def candidates(values, factors):
            return tuple(
                (
                    tuple(factors[f] for f in c.factors.factors),
                    tuple(a.kind.value for a in c.authorities),
                )
                for c in values
            )

        assert candidates(new_region.actual_candidates, new_factors) == candidates(
            old_region.actual_candidates, old_factors
        )

        def pair(value, factors, linkages):
            common = value.common_grain
            return (
                linkages.index(value.left),
                linkages.index(value.right),
                comparison(value.grain_comparison, factors),
                common.status.value,
                candidates(common.actual_candidates, factors),
                tuple(
                    tuple(factors[f] for f in item.candidate.factors.factors)
                    for item in common.common_candidates
                ),
                tuple(
                    tuple(factors[f] for f in item.candidate.factors.factors)
                    for item in common.candidates
                ),
                tuple(
                    tuple(factors[f] for f in item.candidate.factors.factors)
                    for item in value.chasm_candidates
                ),
                value.structural.value,
                None if value.finer is None else linkages.index(value.finer),
                tuple(r.value for r in value.multiplicity_risks),
                tuple(r.value for r in value.requirements),
            )

        assert tuple(
            pair(v, new_factors, observed.grain_linkages)
            for v in observed.pair_linkages
        ) == tuple(
            pair(v, old_factors, expected.grain_linkages)
            for v in expected.pair_linkages
        )
    if original:
        with pytest.raises(ValueError):
            verify_compiled_sql_plan(replace(candidate, aggregate_evidence=()))
        with pytest.raises(ValueError):
            verify_compiled_sql_plan(
                replace(candidate, aggregate_risks=candidate.aggregate_risks[:-1])
            )


def _compare_refinement(artifact):
    from pietto._project.project_refinement import (
        TieRefinement,
        prepare_refinement,
        prepare_compiled_refinement,
    )

    reference = prepare_refinement(
        artifact, capabilities(artifact), policy=TieRefinement()
    )
    built = build_compiled(artifact, refinement=reference)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    candidate = emit_compiled(root, tuple(v.value for v in artifact.fixed_values))
    observed = prepare_compiled_refinement(candidate)
    _compare_refined_structure(reference, observed)


def _compare_refined_structure(reference, observed):
    from pietto._project.project_refinement_rendering import render
    from pietto._project.project_refinement_verification import verify_native
    from pietto._project.project_execution_source import requirement_state

    def descriptor(source):
        state = requirement_state(source)
        assert state is not None
        return state[1:]

    assert tuple(descriptor(s) for s in observed.sources) == tuple(
        descriptor(s) for s in reference.sources
    )
    assert len(observed.units) == len(reference.units)
    assert tuple(
        (
            u.address,
            u.dependencies,
            u.coordinates,
            u.order_coordinates,
            u.directions,
            u.capacity,
        )
        for u in observed.units
    ) == tuple(
        (
            u.address,
            u.dependencies,
            u.coordinates,
            u.order_coordinates,
            u.directions,
            u.capacity,
        )
        for u in reference.units
    )
    assert tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.domain,
            c.realization.nullable,
        )
        for c in observed.output.columns
    ) == tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.domain,
            c.realization.nullable,
        )
        for c in reference.output.columns
    )
    assert tuple(i for i, _ in observed.erasure) == tuple(
        i for i, _ in reference.erasure
    )
    native = render(observed.statement, observed.original)
    assert verify_native(native, observed) == ()


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    (("R2_mixed", "joint"), ("R2_repeated", "tied_limit"), ("R2_bound", "range")),
)
def test_additional_original_refinement_families(tmp_path, target, case, variant):
    from _pietto_execution_source_assurance_cases import original

    _compare(original(tmp_path / "refinement-source", target, case, variant))


def _compare_requirements(reference, observed):
    source = reference.request.report.report
    target = observed.request.report

    def source_ref(value):
        return (
            ("scope", 0)
            if value is reference.request.plan.scope
            else (value.kind.value, value.position)
        )

    def compiled_ref(value):
        return value.kind, value.position

    def owner_key(owner):
        return owner.module_position, owner.declaration_position

    expected = tuple(
        (
            entry.position,
            entry.family.value,
            None if entry.subkind is None else entry.subkind.value,
            source_ref(entry.ref),
            source_ref(entry.subject),
            source_ref(entry.scope.definition),
            tuple(source_ref(r) for r in entry.scope.stages),
            tuple(source_ref(r) for r in entry.scope.input_uses),
            source_ref(entry.origin.ref),
            source_ref(entry.origin.subject),
            entry.origin.role.value,
            entry.origin.provenance.value,
            owner_key(entry.origin.owner),
            tuple(source_ref(r) for r in entry.origin.antecedents),
            (
                entry.origin.cause.span.path,
                entry.origin.cause.span.line,
                entry.origin.cause.span.column,
                entry.origin.cause.span.end_line,
                entry.origin.cause.span.end_column,
            ),
        )
        for entry in source.entries
    )
    actual = tuple(
        (
            entry.position,
            entry.family.value,
            None if entry.subkind is None else entry.subkind.value,
            compiled_ref(entry.ref),
            compiled_ref(entry.subject),
            compiled_ref(entry.scope.definition),
            tuple(compiled_ref(r) for r in entry.scope.stages),
            tuple(compiled_ref(r) for r in entry.scope.input_uses),
            compiled_ref(entry.origin.ref),
            compiled_ref(entry.origin.subject),
            entry.origin.role.value,
            entry.origin.provenance.value,
            owner_key(entry.origin.owner),
            tuple(compiled_ref(r) for r in entry.origin.antecedents),
            entry.origin.location,
        )
        for entry in target.entries
    )
    assert actual == expected
    assert tuple(
        (e.position, e.kind.value, e.source.position, e.target.position)
        for e in target.links
    ) == tuple(
        (e.position, e.kind.value, e.source.position, e.target.position)
        for e in source.links
    )
    assert tuple(r.rule for r in observed.original_requirements) == tuple(
        r.rule for r in reference.original_requirements
    )


@pytest.mark.parametrize("retained", (True, "let", "capture"))
def test_retained_unselected_requests_rederive_without_execution_or_source(
    tmp_path, monkeypatch, retained
):
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project import project_execution_template

    # With "let" the retained request owner is a let of the unselected query,
    # and the compiled closure carries that let without its block. With
    # "capture" the unselected query reads a capturing let by EXISTS.
    source = proof_artifact(tmp_path / "retained-source", retained=retained).artifact
    assert source is not None
    original = prepare_template(source)
    assert len(original.slots) == 1
    expected = []
    for value in (1, 2, 1):
        bound = bind_values(original, ((original.slots[0], value),))
        expected.append(
            tuple(
                (
                    r.request.owner.declaration_position,
                    r.request.scope.value,
                    r.state.value,
                    tuple(p.kind.value for p in r.proofs),
                )
                for r in bound.artifact.request.verification.completed.single_matches.entries
            )
        )
    built = build_compiled(source)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    if retained == "capture":
        import dataclasses
        from pietto._project.project_compiled_schema import CompiledError, Record
        from pietto._project.project_compiled_verification import (
            verify_description,
        )

        # The retained owner's let is inline at its read, and its one capture
        # record is the FROM input row of that owner's reading body.
        description = root.description
        records = {r.address: r for r in description.records}
        (capture,) = (r for r in description.records if r.address.kind == "capture_use")
        block = records[capture.get("read")]
        reader = records[block.get("consumer")]
        assert records[reader.get("owner")].get("label") == "unused"
        assert records[block.get("producer")].get("layout") == (
            None,
            (),
            "s0",
            False,
            None,
        )
        (use,) = (
            r
            for r in description.records
            if r.address.kind == "use" and r.get("consumer") == reader.address
        )
        assert capture.get("ordinal") == 0
        assert capture.get("ports") == use.get("ports")[:2]
        forged = dataclasses.replace(
            description,
            members=tuple(
                (
                    name,
                    tuple(
                        Record(r.address, (r.values[0], 7, r.values[2]))
                        if r.address == capture.address
                        else r
                        for r in group
                    ),
                )
                for name, group in description.members
            ),
        )
        with pytest.raises(CompiledError, match="CAPTURE_ORDINALS"):
            verify_description(forged)
    if retained == "let":
        import dataclasses
        from pietto._project.project_compiled_schema import (
            FIELDS,
            CompiledError,
            Record,
        )
        from pietto._project.project_compiled_verification import (
            verify_description,
        )

        # Moved under the selected query, whose closure never reads it, the
        # retained let is refused: a block reads every let of it.
        description = built.root.description
        names = FIELDS["declaration"]
        (result,) = (
            r
            for r in description.records
            if r.address.kind == "declaration" and r.get("label") == "result"
        )

        def moved(record):
            if record.address.kind != "declaration" or record.get("label") != "j":
                return record
            values = dict(zip(names, record.values, strict=True)) | {
                n: result.get(n) for n in ("module", "module_position", "position")
            }
            return Record(record.address, tuple(values[n] for n in names))

        forged = dataclasses.replace(
            description,
            members=tuple(
                (name, tuple(moved(r) for r in records))
                for name, records in description.members
            ),
        )
        assert forged != description
        with pytest.raises(CompiledError, match="DECLARATION"):
            verify_description(forged)

    def forbidden(*args, **kwargs):
        raise AssertionError("source specialization must not run for a compiled bind")

    monkeypatch.setattr(project_execution_template, "_specialize", forbidden)
    artifact = emit_compiled(root, (1,))
    assert artifact.rendered.sql == source.rendered.sql
    assert len(artifact.request.plan.single_matches) == 1
    assert len(artifact.request.plan.all_single_matches) == 2
    template = prepare_template(artifact)
    assert len(template.slots) == 1
    for value, signatures in zip((1, 2, 1), expected, strict=True):
        bound = bind_values(template, ((template.slots[0], value),))
        plan = bound.artifact.request.plan
        assert len(plan.single_matches) == 1 and len(plan.all_single_matches) == 2
        assert (
            tuple(
                (
                    o.request.owner.declaration_position,
                    o.request.scope.value,
                    o.assessment.state.value,
                    tuple(p.kind.value for p in o.assessment.proofs),
                )
                for o in plan.all_single_matches
            )
            == signatures
        )
        assert bound.artifact.rendered.sql == source.rendered.sql
        assert len(bound.arguments) == 1


def test_a_retained_lateral_join_of_a_capturing_let_is_refused(tmp_path):
    from pietto._project.project_compiled_schema import CompiledError

    # An unselected request owner that joins a capturing let LATERAL has no
    # retained compiled form yet: the build refuses it, never a lookup error.
    source = proof_artifact(tmp_path / "retained-source", retained="lateral").artifact
    assert source is not None
    with pytest.raises(CompiledError, match="COMPILED_RETAINED_CAPTURE"):
        build_compiled(source)


def test_a_retained_collect_read_is_refused(tmp_path):
    from pietto._project.project_compiled_schema import CompiledError

    # D-S09-8: an unselected request owner's Collect read has no retained
    # compiled form (no guarded or R2 owner admits a nested value); the build
    # refuses it before its export, never with a lookup error.
    source = proof_artifact(tmp_path / "retained-source", retained="collect").artifact
    assert source is not None and not source.request.plan.collects
    with pytest.raises(CompiledError, match="COMPILED_RETAINED_COLLECT"):
        build_compiled(source)


def test_a_retained_order_with_a_hidden_key_is_refused(tmp_path):
    from pietto._project.project_compiled_schema import CompiledError

    # An unselected request owner's ORDER BY without DISTINCT carries its key
    # beside the projection, which has no retained compiled form yet: the
    # build refuses it, never a zip error.
    source = proof_artifact(tmp_path / "retained-source", retained="ordered").artifact
    assert source is not None
    with pytest.raises(CompiledError, match="^COMPILED_RETAINED_ORDER$"):
        build_compiled(source)


@pytest.mark.parametrize("shared_reads", (False, True))
def test_retained_unselected_relation_reads_export_and_verify(
    tmp_path, monkeypatch, shared_reads
):
    """An unselected request owner's NOT IN, EXISTS and scalar reads export and
    verify like the selected path's: each operation names one block use of its actual
    producer, a producer reached only through such a read is retained, a read
    of a relation shared with the selected statement stays one block use, and
    the loaded replay is the source statement."""
    from dataclasses import replace
    from pietto._project import project_compiled_verification as verification
    from pietto._project.project_compiled_schema import CompiledError, Record

    original = emission.join_witness
    projection = "    select:\n        value = lhs.id\n"

    def with_reads(target, body, **options):
        selected, unused = body.split("query unused:", 1)
        if shared_reads:
            selected = selected.replace(
                projection, "    where lhs.id in ranked_ids\n" + projection
            ).replace(
                "    from rhs\n", "    from rhs\n    where id not in ranked_ids\n", 1
            )
        unused = unused.replace(
            projection,
            "    where lhs.id not in ranked_ids\n"
            + projection
            + "        seen = exists ranked_ids\n"
            + "        top = scalar ranked_ids.id\n",
        )
        return original(
            target,
            "query ranked_ids:\n    from rhs\n    select:\n        id\n"
            + selected
            + "query unused:"
            + unused,
            **options,
        )

    captured = []
    checker = verification.verify_logical_export

    def capture(description, checked, references):
        checker(description, checked, references)
        captured.append((description, checked, references))

    monkeypatch.setattr(emission, "join_witness", with_reads)
    monkeypatch.setattr(verification, "verify_logical_export", capture)
    source = proof_artifact(tmp_path / "retained-reads", retained=True).artifact
    assert source is not None
    built = build_compiled(source)
    records = built.root.records

    def label(address):
        return records[records[address].get("owner")].get("label")

    assert [
        (
            records[r.get("operation")].get("operator"),
            r.get("column"),
            label(r.get("producer")),
            label(r.get("consumer")),
        )
        for r in records.values()
        if r.address.kind == "expression_block_use"
    ] == [
        *(
            [
                (("relation_membership", "not_in"), 0, "ranked_ids", "ranked"),
                (("relation_membership", "in"), 0, "ranked_ids", "result"),
            ]
            * shared_reads
        ),
        (("relation_membership", "not_in"), 0, "ranked_ids", "unused"),
        (("exists", "exists"), None, "ranked_ids", "unused"),
        (("scalar", "scalar"), 0, "ranked_ids", "unused"),
    ]
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, tuple(v.value for v in source.fixed_values))
    assert replay.rendered.sql == source.rendered.sql
    # The retained component is re-derived from its own plan: another
    # operator or another producer for its membership read, and another
    # operator or no column for its scalar read, are refused.
    ((child, checked, references),) = captured
    described = {r.address: r for r in child.records}
    membership, scalar_read = (
        r
        for r in described.values()
        if r.address.kind == "expression_block_use"
        and r.get("column") == 0
        and described[described[r.get("consumer")].get("owner")].get("label")
        == "unused"
    )
    operation = described[membership.get("operation")]
    scalar_operation = described[scalar_read.get("operation")]
    assert scalar_operation.get("operator") == ("scalar", "scalar")
    for changed, word in (
        (
            Record(
                operation.address,
                (("relation_membership", "in"), *operation.values[1:]),
            ),
            "EXPRESSION",
        ),
        (
            Record(
                membership.address,
                (*membership.values[:2], membership.get("consumer"), 0),
            ),
            "BLOCK_READ",
        ),
        (
            Record(
                scalar_operation.address,
                (("exists", "exists"), *scalar_operation.values[1:]),
            ),
            "EXPRESSION",
        ),
        (Record(scalar_read.address, (*scalar_read.values[:3], None)), "BLOCK_READ"),
    ):
        forged = replace(
            child,
            members=tuple(
                (
                    name,
                    tuple(
                        changed if r.address == changed.address else r for r in group
                    ),
                )
                for name, group in child.members
            ),
        )
        with pytest.raises(CompiledError, match=f"^COMPILED_RETAINED_{word}$"):
            checker(forged, checked, references)


def test_embedded_json_depth_is_checked_before_decoder_recursion(tmp_path):
    from dataclasses import replace
    from _pietto_execution_postgres_rows_probe import template
    from pietto._project.project_compiled_schema import (
        Record,
        MAX_DEPTH,
        encode,
        content_pin,
        CompiledError,
    )

    source = template(tmp_path / "bounded-source")
    built = build_compiled(source.artifact)
    for kind, field in (
        ("field", "physical"),
        ("target", "contract"),
        ("premise", "value"),
    ):
        target = next(
            r for r in built.root.description.records if r.address.kind == kind
        )
        values = list(target.values)
        from pietto._project.project_compiled_schema import FIELDS

        values[FIELDS[kind].index(field)] = (
            "[" * (MAX_DEPTH + 1) + "0" + "]" * (MAX_DEPTH + 1)
        )
        damaged = Record(target.address, tuple(values))
        description = replace(
            built.root.description,
            members=tuple(
                (
                    name,
                    tuple(
                        damaged if r.address == target.address else r for r in records
                    ),
                )
                for name, records in built.root.description.members
            ),
        )
        raw = encode(description)
        with pytest.raises(CompiledError, match="^COMPILED_DEPTH_LIMIT$"):
            load_compiled(
                raw,
                expected_pin=content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )


def test_repinned_slot_and_requirement_damage_refuses(tmp_path):
    from dataclasses import replace
    from _pietto_execution_postgres_rows_probe import template
    import _pietto_results_product as product
    from pietto._project.project_compiled_schema import (
        FIELDS,
        Record,
        encode,
        content_pin,
    )

    source = template(
        tmp_path / "damage-source",
        product.source("postgres").replace(
            "renamed = id", "renamed = 1\n        another = 1"
        ),
    )
    built = build_compiled(source.artifact)
    records = built.root.description.records
    slots = tuple(r for r in records if r.address.kind == "slot")
    assert len(slots) == 2
    first_site = built.root.records[slots[0].get("site")]

    def altered(record, **changes):
        values = list(record.values)
        for name, value in changes.items():
            values[FIELDS[record.address.kind].index(name)] = value
        return Record(record.address, tuple(values))

    damages = (
        altered(first_site, role="limit"),
        altered(first_site, ancestry=(("unary", 0),)),
        altered(slots[1], site=slots[0].get("site"), literal=slots[0].get("literal")),
        altered(
            next(r for r in records if r.address.kind == "requirement"), family="window"
        ),
        altered(
            next(r for r in records if r.address.kind == "target"),
            profile="finite_mysql_v1",
        ),
    )
    codes = (
        "SLOT_ELIGIBILITY",
        "SLOT_ANCESTRY",
        "SLOT_ALIAS",
        "REQUIREMENT_SUBKIND",
        "PROFILE",
    )
    for damaged, code in zip(damages, codes, strict=True):
        description = replace(
            built.root.description,
            members=tuple(
                (
                    name,
                    tuple(
                        damaged if r.address == damaged.address else r for r in members
                    ),
                )
                for name, members in built.root.description.members
            ),
        )
        raw = encode(description)
        with pytest.raises(ValueError, match="^COMPILED_%s$" % code):
            load_compiled(
                raw,
                expected_pin=content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )


def test_repinned_cross_family_comparison_refuses_derivation_and_verification(
    tmp_path, monkeypatch
):
    from dataclasses import replace
    from _pietto_execution_postgres_rows_probe import template
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_completed_semantics import (
        derive_compiled_semantics,
        verify_compiled_semantics,
    )
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Record,
        Scalar,
        content_pin,
        encode,
    )
    from pietto.semantic import expressions
    from pietto.semantic.model import (
        EffectiveNullability,
        ResolvedType,
        TypeKind,
        ValueType,
    )

    # The default template filters `id > 1` with the literal bound to an Int slot.
    built = build_compiled(template(tmp_path / "comparison-source").artifact)
    records = built.root.description.records
    slot = next(r for r in records if r.address.kind == "slot")
    literal = built.root.records[slot.get("literal")]

    def altered(record, **changes):
        values = list(record.values)
        for name, value in changes.items():
            values[FIELDS[record.address.kind].index(name)] = value
        return Record(record.address, tuple(values))

    damaged = {
        r.address: r
        for r in (
            altered(literal, tag="Text", value=Scalar("Text", "1")),
            altered(slot, tag="Text"),
        )
    }
    description = replace(
        built.root.description,
        members=tuple(
            (name, tuple(damaged.get(r.address, r) for r in members))
            for name, members in built.root.description.members
        ),
    )
    raw = encode(description)
    root = load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    # The shared comparison law refuses Int > Text before any physical check.
    with pytest.raises(CompiledError, match="^COMPILED_OPERATOR_TYPE$"):
        derive_compiled_semantics(root, ("1",))

    # A derivation forged past the law and the physical comparison check is
    # still refused by the independent verifier.
    with monkeypatch.context() as patch:
        unchecked = (
            ValueType(
                ResolvedType("Bool", TypeKind.BUILTIN), EffectiveNullability.UNKNOWN
            ),
            None,
        )
        patch.setattr(
            expressions, "resolved_comparison_value_type", lambda *_: unchecked
        )
        patch.setattr(
            physical,
            "resolved_comparison_realization",
            lambda family, tag, nullable, left, right, **_: (
                physical._bool(family, False),
                None,
            ),
        )
        forged = derive_compiled_semantics(root, ("1",))
    with pytest.raises(CompiledError, match="^COMPILED_SEMANTIC_TYPE$"):
        verify_compiled_semantics(forged)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_compiled_premises_preserve_original_admission(tmp_path, target):
    """A correct external test pin must not hide invalid semantic premises."""
    import copy
    import json
    from dataclasses import replace
    from pietto._project.project_compiled_schema import (
        Address,
        Record,
        encode,
        content_pin,
    )
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_sql_emission_contract import canonical

    source = build(
        tmp_path / "premise-source", target, "S_fixed_named", "imported_bind"
    ).artifact
    assert source is not None
    built = build_compiled(source)
    described = built.root.description
    original_contract = json.loads(source.request.accepted_bytes)
    original_premises = tuple(
        r for r in described.records if r.address.kind == "premise"
    )

    def load(contract, premises):
        target_record = built.root.records[Address("target", 0)]
        changed_target = Record(
            target_record.address,
            (
                *target_record.values[:2],
                canonical(contract).decode(),
                target_record.values[3],
            ),
        )
        changed_premises = tuple(
            Record(Address("premise", i), (i, *r.values[1:]))
            for i, r in enumerate(premises)
        )
        description = replace(
            described,
            members=tuple(
                (
                    name,
                    tuple(
                        changed_target if r.address.kind == "target" else r
                        for r in records
                        if r.address.kind != "premise"
                    )
                    + (changed_premises if name == "targets" else ()),
                )
                for name, records in described.members
            ),
        )
        raw = encode(description)
        return load_compiled(
            raw,
            expected_pin=content_pin(raw),
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )

    # Expected rejection comes from the original source emitter and its real roots.
    for key, value, code in (
        ("operator_environment", "unqualified_operators", "OPERATOR_PREMISE"),
        ("parameter_protocol", "interpolated_text", "OPERATOR_PREMISE"),
        ("identifier_case", "case_folded", "NAMING_PREMISE"),
        ("client_encoding", "LATIN1", "SOURCE_PREMISE"),
        ("row_domain_matches", False, "SOURCE_PREMISE"),
        ("read_only_object", False, "SOURCE_PREMISE"),
        ("row_domain_matches", 1, "PREMISE_VALUE"),
    ):
        contract = copy.deepcopy(original_contract)
        raw_premises = contract["environment"] + [
            p for s in contract["sources"] for p in s["premises"]
        ]
        assert any(p["key"] == key for p in raw_premises)
        for p in raw_premises:
            if p["key"] == key:
                p["value"] = value
        outcome = emit_project_sql(source.request.verification, canonical(contract))
        assert outcome.status in ("INPUT_REJECTED", "BLOCKED"), key
        premises = tuple(
            Record(r.address, (*r.values[:3], canonical(value).decode()))
            if r.get("key") == key
            else r
            for r in original_premises
        )
        with pytest.raises(ValueError, match="^COMPILED_%s$" % code):
            load(contract, premises)

    for key, code in (
        ("operator_environment", "OPERATOR"),
        ("parameter_protocol", "OPERATOR"),
        ("client_encoding", "SOURCE"),
        ("row_domain_matches", "SOURCE"),
        ("read_only_object", "SOURCE"),
    ):
        contract = copy.deepcopy(original_contract)
        contract["environment"] = [
            p for p in contract["environment"] if p["key"] != key
        ]
        for s in contract["sources"]:
            s["premises"] = [p for p in s["premises"] if p["key"] != key]
        outcome = emit_project_sql(source.request.verification, canonical(contract))
        assert outcome.status == "BLOCKED", key
        with pytest.raises(ValueError, match="^COMPILED_%s_PREMISE$" % code):
            load(contract, tuple(r for r in original_premises if r.get("key") != key))

    # Preserve the original distinction between equal repeats and conflicts.
    first = next(
        i
        for i, r in enumerate(original_premises)
        if r.get("key") == "operator_environment"
    )
    for value, accepted in (("builtin_only", True), ("unqualified_operators", False)):
        contract = copy.deepcopy(original_contract)
        index = next(
            i
            for i, p in enumerate(contract["environment"])
            if p["key"] == "operator_environment"
        )
        contract["environment"].insert(
            index + 1, dict(key="operator_environment", scope="statement", value=value)
        )
        extra = Record(
            original_premises[first].address,
            (*original_premises[first].values[:3], canonical(value).decode()),
        )
        premises = (
            *original_premises[: first + 1],
            extra,
            *original_premises[first + 1 :],
        )
        outcome = emit_project_sql(source.request.verification, canonical(contract))
        assert (outcome.status == "VERIFIED") is accepted
        if accepted:
            root = load(contract, premises)
            assert (
                emit_compiled(
                    root, tuple(v.value for v in source.fixed_values)
                ).rendered.sql
                == source.rendered.sql
            )
        else:
            with pytest.raises(ValueError, match="^COMPILED_PREMISE_CONFLICT$"):
                load(contract, premises)

    # The raw contract and resolved graph must agree independently and completely.
    for damage, code in (
        ("missing_record", "PREMISES"),
        ("extra_field", "SOURCE"),
        ("wrong_scan", "SOURCE"),
        ("bool_ordinal", "FIELD"),
        ("wrong_source_scope", "PREMISE_SCOPE"),
    ):
        contract = copy.deepcopy(original_contract)
        premises = original_premises
        if damage == "missing_record":
            premises = premises[:-1]
        elif damage == "extra_field":
            contract["sources"][0]["unexpected"] = True
        elif damage == "wrong_scan":
            contract["sources"][0]["scan"] = "raw_sql"
        elif damage == "bool_ordinal":
            contract["sources"][0]["fields"][0]["ordinal"] = False
        else:
            contract["sources"][0]["premises"][0]["scope"] = "statement"
        with pytest.raises(ValueError, match="^COMPILED_CONTRACT_%s$" % code):
            load(contract, premises)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "variant", ("limit", "global", "grouped", "window", "set", "ordered", "key")
)
def test_retained_unselected_request_does_not_require_execution_mapping(
    tmp_path, monkeypatch, target, variant
):
    from dataclasses import replace
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project import project_compiled_verification as verification
    from pietto._project.project_compiled_schema import (
        Address,
        Record,
        FIELDS,
        encode,
        content_pin,
    )

    outcome = retained_unmapped_source(
        tmp_path / "unselected-unmapped", target, variant, monkeypatch
    )
    assert outcome.status == "VERIFIED", tuple(
        (b.code, b.detail) for b in outcome.blockers
    )
    source = outcome.artifact
    assert source is not None
    assert len(source.request.verification.completed.single_match_requests) == 2
    assert len(source.request.sources) == 2
    # The actual source binding route retains this request without admitting or
    # evaluating the unrelated physical source.
    reference = prepare_template(source)
    accepted = bind_values(reference, tuple((slot, 2) for slot in reference.slots))
    captured = []
    checker = verification.verify_logical_export

    def capture(description, checked, correspondence):
        checker(description, checked, correspondence)
        captured.append((description, checked, correspondence.copy()))

    monkeypatch.setattr(verification, "verify_logical_export", capture)
    built = build_compiled(source)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    template = prepare_template(
        emit_compiled(loaded, tuple(v.value for v in source.fixed_values))
    )
    bound = bind_values(template, tuple((slot, 2) for slot in template.slots))
    assert bound.artifact.rendered.sql == accepted.artifact.rendered.sql
    assert len(bound.artifact.request.plan.all_single_matches) == 2
    assert len(bound.artifact.request.plan.single_matches) == 1
    assert len(bound.artifact.request.sources) == 2
    assert tuple(
        (
            a.request.owner.declaration_position,
            a.request.scope.value,
            a.assessment.state.value,
            tuple(p.kind.value for p in a.assessment.proofs),
        )
        for a in bound.artifact.request.plan.all_single_matches
    ) == tuple(
        (
            a.request.owner.declaration_position,
            a.request.scope.value,
            a.state.value,
            tuple(p.kind.value for p in a.proofs),
        )
        for a in accepted.artifact.request.verification.completed.single_matches.entries
    )
    logical_sources = tuple(
        r
        for r in loaded.description.records
        if r.address.kind == "source" and r.get("namespace") is None
    )
    assert len(logical_sources) == 1
    assert all(
        loaded.records[f].get("physical") is None
        for f in logical_sources[0].get("fields")
    )

    assert len(captured) == 1
    description, checked, correspondence = captured[0]

    def changed_record(record, **changes):
        values = list(record.values)
        for name, value in changes.items():
            values[FIELDS[record.address.kind].index(name)] = value
        return Record(record.address, tuple(values))

    field = next(r for r in description.records if r.address.kind == "field")
    use = next(r for r in description.records if r.address.kind == "use")
    request = next(r for r in description.records if r.address.kind == "request")
    damages = [
        changed_record(field, logical=("Bool", "non_null")),
        changed_record(use, ordinal=99),
        changed_record(
            request, pairs=tuple(pair[::-1] for pair in request.get("pairs"))
        ),
    ]
    codes = ("SOURCE_FIELD", "USE_INPUT", "REQUEST_INPUTS")
    for damage, code in zip(damages, codes, strict=True):
        candidate = replace(
            description,
            members=tuple(
                (
                    name,
                    tuple(
                        damage if r.address == damage.address else r for r in records
                    ),
                )
                for name, records in description.members
            ),
        )
        with pytest.raises(ValueError, match="^COMPILED_RETAINED_%s$" % code):
            checker(candidate, checked, correspondence)
    removed = {"site"}
    if variant == "key":
        removed.add("source_unique")
    for kind in removed:
        assert any(r.address.kind == kind for r in description.records), kind
        candidate = replace(
            description,
            members=tuple(
                (name, tuple(r for r in records if r.address.kind != kind))
                for name, records in description.members
            ),
        )
        code = {"site": "LITERAL", "source_unique": "KEY"}[kind]
        with pytest.raises(ValueError, match="^COMPILED_RETAINED_%s_INVENTORY$" % code):
            checker(candidate, checked, correspondence)

    # A retained logical source cannot become an executable source by changing
    # the selected entry, even with a correct independent test pin.
    entry = loaded.records[loaded.description.query]
    terminal = loaded.records[entry.get("retained")[0]]
    changed = changed_record(
        entry,
        declaration=terminal.get("owner"),
        terminal=terminal.address,
        exports=terminal.get("outputs"),
        retained=(entry.get("terminal"),),
    )
    selected_outputs = tuple(
        Record(
            Address("output", i),
            (
                i,
                loaded.records[port].get("label"),
                port,
                loaded.records[port].get("logical"),
                None,
            ),
        )
        for i, port in enumerate(terminal.get("outputs"))
    )
    candidate = replace(
        loaded.description,
        members=tuple(
            (
                name,
                selected_outputs
                if name == "outputs"
                else tuple(
                    changed if r.address == entry.address else r for r in records
                ),
            )
            for name, records in loaded.description.members
        ),
    )
    raw = encode(candidate)
    with pytest.raises(ValueError, match="^COMPILED_SOURCE$"):
        load_compiled(
            raw,
            expected_pin=content_pin(raw),
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )


# Phase70 S12: a JOIN reads a let with capture lines LATERAL; the let compiles
# inline at that JOIN's right input and each capture_use record names that
# right input's use, its capturing read.
LATERAL_LET = """    let {name}:
        capture lhs
        from rhs
        where rhs.{field} == lhs.{field}
        select:
            id
{tail}    from lhs
"""
TWO_LATERAL = (
    "table a:\n"
    + LATERAL_LET.format(name="m", field="key", tail="")
    + "    let m1 = m\n    cross join m1\n"
    + "    select:\n        id = lhs.id\n        t = m1.id\n"
    + "table b:\n"
    + LATERAL_LET.format(name="n", field="id", tail="")
    + "    let n1 = n\n    inner join n1 on True\n"
    + "    select:\n        id = lhs.id\n        t = n1.id\n"
    + "query result:\n    from a\n    let y = b\n    cross join y\n"
    + "    select:\n        x = a.t\n        z = y.t\n"
)
TOP_K_LATERAL = (
    "query result:\n"
    + LATERAL_LET.format(
        name="m",
        field="key",
        tail="            v = rhs.key\n        order by:\n            key desc\n"
        "            id\n        limit 2\n",
    )
    + "    let m1 = m\n    {kind} join m1{on}\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n"
)


def _compiled_lateral(directory, target, source):
    """The verified source artifact, its compiled build and the loaded replay."""
    from pietto._project.project_compiled_schema import encode

    item = emission.join_witness(target, source, policy="bind_safe_literals")
    checked, original = emission.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    artifact = original.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert encode(loaded.description) == built.payload
    candidate = emit_compiled(loaded, tuple(v.value for v in artifact.fixed_values))
    assert candidate.rendered.sql == artifact.rendered.sql
    return artifact, built, candidate


def _replaced(description, targets):
    """``description`` with the values of the records in ``targets`` replaced."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import Record

    return replace(
        description,
        members=tuple(
            (
                name,
                tuple(
                    Record(r.address, targets[r.address]) if r.address in targets else r
                    for r in records
                ),
            )
            for name, records in description.members
        ),
    )


def _load(raw, built):
    from pietto._project.project_compiled_schema import content_pin

    return load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )


def _captured_references(query):
    """Every captured reference of a lowered statement, by its scope alias."""
    import dataclasses
    from pietto._project import project_sql_emission_rows as rows

    found, pending, seen = {}, list(query.bodies), set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if type(value) is rows.SQLCapturedReference:
            found.setdefault(value.scope.name, []).append(value)
        if type(value) is tuple:
            pending.extend(value)
        elif dataclasses.is_dataclass(value) and type(value).__module__.startswith(
            "pietto._project.project_sql_emission"
        ):
            pending.extend(getattr(value, f.name) for f in dataclasses.fields(value))
    return found


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_two_lateral_lets_capturing_one_source_replay_by_their_reads(tmp_path, target):
    from pietto._project.project_compiled_schema import CompiledError, encode
    from pietto._project.project_compiled_verification import (
        verify_compiled_emission,
        verify_description,
    )

    # Two tables each join their own let LATERAL over the same source lhs: the
    # two capture records name the same source ports through distinct reads.
    artifact, built, candidate = _compiled_lateral(tmp_path, target, TWO_LATERAL)
    description = built.root.description
    records = {r.address: r for r in description.records}
    first, second = (r for r in description.records if r.address.kind == "capture_use")
    assert first.get("ports") == second.get("ports")
    assert first.get("read") != second.get("read")
    for record in (first, second):
        right = records[record.get("read")]
        assert (right.address.kind, right.get("ordinal"), record.get("ordinal")) == (
            "use",
            1,
            0,
        )
        assert records[right.get("consumer")].address.kind == "join"
    # Each captured reference names the record of its own JOIN's read.
    captured = _captured_references(candidate.ast)
    assert {
        alias: [r.capture.ref.position for r in found]
        for alias, found in captured.items()
    } == {"m0": [0], "m2": [1]}
    # Swapped between the two reads, a valid record of the same port is refused
    # by the compiled emission verifier.
    (left,), (right,) = captured["m0"], captured["m2"]
    original = left.capture, right.capture
    object.__setattr__(left, "capture", original[1])
    object.__setattr__(right, "capture", original[0])
    try:
        with pytest.raises(CompiledError, match="^COMPILED_EMISSION_CAPTURE$"):
            verify_compiled_emission(candidate, candidate.request)
    finally:
        object.__setattr__(left, "capture", original[0])
        object.__setattr__(right, "capture", original[1])
    verify_compiled_emission(candidate, candidate.request)
    # Both records naming one read leave the other read without its let.
    with pytest.raises(CompiledError, match="^COMPILED_INLINE_INVENTORY$"):
        verify_description(
            _replaced(
                description, {second.address: (first.get("read"), *second.values[1:])}
            )
        )
    # The two records swapped whole are the same captures renumbered: each
    # read still finds its own record, and the replay is the same statement.
    swapped = _replaced(
        description, {first.address: second.values, second.address: first.values}
    )
    verify_description(swapped)
    replay = emit_compiled(
        _load(encode(swapped), built), tuple(v.value for v in artifact.fixed_values)
    )
    assert replay.rendered.sql == artifact.rendered.sql
    assert {
        alias: [r.capture.ref.position for r in found]
        for alias, found in _captured_references(replay.ast).items()
    } == {"m0": [1], "m2": [0]}


def test_a_lateral_lets_inline_units_name_no_input_of_its_join(tmp_path):
    # Its correlated references name the JOIN's left input: no unit of the
    # let, its ORDER BY and LIMIT included, takes a JOIN input's alias, and no
    # two of its units share one. Another unit's scope may repeat an alias.
    from pietto._project.project_compiled_schema import FIELDS, CompiledError, encode
    from pietto._project.project_compiled_verification import verify_description

    source = TOP_K_LATERAL.format(kind="cross", on="")
    _, built, _ = _compiled_lateral(tmp_path, "postgres", source)
    description = built.root.description
    (join,) = (r for r in description.records if r.address.kind == "join")
    inline = [
        r
        for r in description.records
        if "layout" in FIELDS[r.address.kind] and r.get("layout")[-1] is None
    ]
    assert [r.address.kind for r in inline] == ["row", "row", "result"]
    names = [r.get("layout")[2] for r in inline]
    assert join.get("layout")[2] == ("m0", "m1")

    def aliased(record, alias):
        values = list(record.values)
        at = FIELDS[record.address.kind].index("layout")
        layout = values[at]
        values[at] = (*layout[:2], alias, *layout[3:])
        return _replaced(description, {record.address: tuple(values)})

    forgeries = [aliased(unit, "m0") for unit in inline]
    forgeries += [aliased(join, ("m0", name)) for name in names]
    forgeries.append(aliased(inline[2], names[0]))
    for forged in forgeries:
        with pytest.raises(CompiledError, match="^COMPILED_ALIASES$"):
            verify_description(forged)
        with pytest.raises(CompiledError, match="^COMPILED_ALIASES$"):
            _load(encode(forged), built)


@pytest.mark.parametrize("kind", ("right", "full", "semi", "anti"))
def test_a_compiled_lateral_join_keeps_a_kind_that_extends_each_left_row(
    tmp_path, kind
):
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        encode,
    )
    from pietto._project.project_compiled_verification import verify_description

    source = TOP_K_LATERAL.format(kind="left", on=" on m1.id > 3")
    _, built, _ = _compiled_lateral(tmp_path, "postgres", source)
    description = built.root.description
    (join,) = (r for r in description.records if r.address.kind == "join")
    assert join.get("kind") == "left"
    # Otherwise valid: a SEMI or ANTI JOIN outputs only its left input.
    names = FIELDS["join"]
    values = list(join.values)
    values[names.index("kind")] = kind
    if kind in ("semi", "anti"):
        left = next(
            r for r in description.records if r.address == join.get("inputs")[0]
        )
        values[names.index("outputs")] = join.get("outputs")[: len(left.get("ports"))]
    forged = _replaced(description, {join.address: tuple(values)})
    with pytest.raises(CompiledError, match="^COMPILED_LATERAL_JOIN_KIND$"):
        verify_description(forged)
    with pytest.raises(CompiledError, match="^COMPILED_LATERAL_JOIN_KIND$"):
        _load(encode(forged), built)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("cross", "inner", "left"))
def test_a_lateral_top_k_replays_from_compiled_input(tmp_path, target, kind):
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Scalar,
    )
    from pietto._project.project_compiled_verification import (
        verify_description,
        verify_export,
    )

    on = {"cross": "", "inner": " on True", "left": " on m1.id > 3"}
    artifact, built, candidate = _compiled_lateral(
        tmp_path, target, TOP_K_LATERAL.format(kind=kind, on=on[kind])
    )
    assert b" LIMIT 2) AS " in candidate.rendered.sql
    # The let's ORDER BY and LIMIT are one inline result unit, read by the
    # JOIN's right input: no unit position, no CTE name, not final.
    description = built.root.description
    records = {r.address: r for r in description.records}
    (capture,) = (r for r in description.records if r.address.kind == "capture_use")
    result = records[records[capture.get("read")].get("producer")]
    assert result.address.kind == "result"
    assert result.get("layout") == (None, (), "t0", False, None)
    assert (result.get("distinct"), result.get("limit")) == (False, 2)
    assert [d for _, d in result.get("ordering")] == ["desc", "asc"]
    projection = records[result.get("input")]
    assert projection.address.kind == "row" and projection.get("layout")[-1] is None
    names = FIELDS["result"]

    def changed(**fields):
        values = list(result.values)
        for name, value in fields.items():
            values[names.index(name)] = value
        return _replaced(description, {result.address: tuple(values)})

    layout = result.get("layout")
    # Claiming a unit position or a CTE name makes it no inline unit.
    with pytest.raises(CompiledError, match="^COMPILED_CAPTURE_USE$"):
        verify_description(changed(layout=(*layout[:-1], 0)))
    with pytest.raises(CompiledError, match="^COMPILED_INLINE_LAYOUT$"):
        verify_description(changed(layout=("p9", *layout[1:])))
    # Another valid LIMIT with its literal is a coherent description; the
    # export verifier re-derives it from the live statement and refuses it.
    literal = records[result.get("limit_literal")]
    values = list(literal.values)
    values[FIELDS["literal"].index("value")] = Scalar("Int", 3)
    limit = list(result.values)
    limit[names.index("limit")] = 3
    forged = _replaced(
        description, {result.address: tuple(limit), literal.address: tuple(values)}
    )
    verify_description(forged)
    with pytest.raises(CompiledError, match="^COMPILED_EXPORT_STATIC_LITERAL$"):
        verify_export(forged, artifact)


# Owner decision 2026-10-15 (D70.05): a correlated NOT IN and a scalar read of
# two lets ending in ORDER BY and LIMIT compile on PostgreSQL with no new
# record kind: each let's ORDER BY and LIMIT are one inline result unit, the
# outermost of its chain, read by the expression block use of its read.
ORDERED_BLOCK_READS = (
    "query result:\n    let m:\n        capture lhs\n        from rhs\n"
    "        where rhs.key == lhs.key\n        select:\n            id\n"
    "        order by:\n            id desc\n        limit 2\n"
    "    let n:\n        capture lhs\n        from rhs\n"
    "        where rhs.id == lhs.id\n        select:\n            key\n"
    "        order by:\n            id\n        limit 1\n"
    "    from lhs\n    where lhs.id not in m\n"
    "    select:\n        a = lhs.id\n        k = scalar n.key\n"
)


def test_ordered_scalar_and_in_reads_replay_from_compiled_input(tmp_path):
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Scalar,
    )
    from pietto._project.project_compiled_verification import (
        verify_description,
        verify_export,
    )

    artifact, built, candidate = _compiled_lateral(
        tmp_path, "postgres", ORDERED_BLOCK_READS
    )
    sql = candidate.rendered.sql
    assert (sql.count(b" LIMIT 2) AS "), sql.count(b" LIMIT 1) AS ")) == (1, 1)
    description = built.root.description
    records = {r.address: r for r in description.records}
    captures = [r for r in description.records if r.address.kind == "capture_use"]
    reads = [records[c.get("read")] for c in captures]
    assert [r.address.kind for r in reads] == ["expression_block_use"] * 2
    results = [records[r.get("producer")] for r in reads]
    assert sorted(
        (r.address.kind, r.get("layout")[:2], r.get("layout")[3:], r.get("limit"))
        for r in results
    ) == [
        ("result", (None, ()), (False, None), 1),
        ("result", (None, ()), (False, None), 2),
    ]
    result = results[0]
    names = FIELDS["result"]
    layout = result.get("layout")
    # A unit position makes it no inline unit of the read.
    values = list(result.values)
    values[names.index("layout")] = (*layout[:-1], 0)
    with pytest.raises(CompiledError, match="^COMPILED_CAPTURE_USE$"):
        verify_description(_replaced(description, {result.address: tuple(values)}))
    # Another valid LIMIT with its literal is a coherent description that the
    # export verifier refuses against the live statement.
    literal = records[result.get("limit_literal")]
    literal_values = list(literal.values)
    literal_values[FIELDS["literal"].index("value")] = Scalar("Int", 3)
    values = list(result.values)
    values[names.index("limit")] = 3
    forged = _replaced(
        description,
        {result.address: tuple(values), literal.address: tuple(literal_values)},
    )
    verify_description(forged)
    with pytest.raises(CompiledError, match="^COMPILED_EXPORT_STATIC_LITERAL$"):
        verify_export(forged, artifact)


def test_a_mysql_description_of_an_ordered_block_read_is_refused(tmp_path, monkeypatch):
    # MySQL reads a let's ORDER BY and LIMIT only LATERAL. A MySQL artifact
    # forged past the emission's own refusal and its verifiers describes a
    # scalar or IN read of an inline result unit; the emission verifier and
    # the compiled description (a repinned bundle) each refuse it on their own.
    from types import SimpleNamespace

    from pietto._project import project_sql_emission as emitting
    from pietto._project import project_sql_emission_ast as sql_ast
    from pietto._project import project_sql_emission_inspection as inspection
    from pietto._project.project_compiled_build import _Export
    from pietto._project.project_compiled_schema import CompiledError, encode
    from pietto._project.project_compiled_verification import verify_description
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    verified = SimpleNamespace(verified=True, issues=())
    monkeypatch.setattr(
        sql_ast, "ORDERED_INLINE_READ_TARGETS", frozenset({"postgres", "mysql"})
    )
    monkeypatch.setattr(emitting, "verify_row_query", lambda *_: True)
    for module in (emitting, inspection):
        monkeypatch.setattr(module, "verify_project_sql_emission", lambda *_: verified)
    item = emission.join_witness("mysql", ORDERED_BLOCK_READS)
    _, outcome = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    artifact = outcome.artifact
    assert artifact is not None and b" LIMIT 1) AS " in artifact.rendered.sql
    description = _Export(artifact, None, None).run()
    monkeypatch.undo()
    assert not verify_project_sql_emission(artifact, artifact.request).verified
    with pytest.raises(CompiledError, match="^COMPILED_MYSQL_CORRELATED_ORDER$"):
        verify_description(description)
    built = SimpleNamespace(
        producer=description.producer, compatibility=description.compatibility
    )
    with pytest.raises(CompiledError, match="^COMPILED_MYSQL_CORRELATED_ORDER$"):
        _load(encode(description), built)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("left", "inner"))
def test_an_asof_join_emits_its_latest_row_as_an_anti_join_and_replays(
    tmp_path, kind, target
):
    """A project asof JOIN is the JOIN plus `not any(...)` of a later row: the
    emitted, compiled-replay and live-template SQL are one statement, on MySQL
    with its own quotes."""
    source = CANONICAL.replace("query order_prices", "query result").replace(
        "asof left join", f"asof {kind} join"
    )
    if target == "mysql":
        source = source.replace("postgres.table", "mysql.table")
    checked, outcome = emission.build_case(tmp_path, source, project_contract(target))
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    expected = (
        f'{kind.upper()} JOIN "shop"."prices" AS "m1" ON ((("m0"."product_id" = '
        '"m1"."product_id") AND ("m0"."ordered_at" >= "m1"."valid_from")) AND (NOT '
        'EXISTS (SELECT 1 FROM "shop"."prices" AS "e0" WHERE ((("m0"."product_id" = '
        '"e0"."product_id") AND ("m0"."ordered_at" >= "e0"."valid_from")) AND '
        '("e0"."valid_from" > "m1"."valid_from")))))'
    )
    if target == "mysql":
        expected = expected.replace('"', "`")
    assert expected.encode() in sql
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(value.value for value in outcome.artifact.fixed_values)
    assert emit_compiled(loaded, values).rendered.sql == sql
    assert prepare_live_template(outcome.artifact).artifact.rendered.sql == sql


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_max_and_min_of_two_values_emit_replay_and_bind_one_statement(tmp_path, target):
    """`max(a, b)` and `min(a, b)` are the conditionals they mean, None when
    either value is: the emitted, compiled-replay and live-template SQL are one
    statement, and the result is nullable only where an argument is. A Bool
    pair, which project SQL does not order, stays refused."""
    base = emission.parameterized_fixture(target, "", protocol=False)
    header = base["source"].replace("    text: Text\n", "    text: Text | None\n")
    contract = json.loads(base["contract"])
    (text,) = (f for f in contract["sources"][0]["fields"] if f["name"] == "text")
    text["representation"]["nullable"] = True
    body = (
        "table result:\n    from rows\n    select:\n        id\n"
        "        hi = max(id, 3)\n"
        '        word = min(text, "m")\n'
        "        top = max(money, money)\n"
        "        low = min(ratio, ratio)\n"
        "        late = max(text, text)\n"
    )
    encoded = emission.encoded(contract).decode()
    checked, outcome = emission.build_case(tmp_path / "ok", header + body, encoded)
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    field, late = (
        ('"s0"."text `""é"', '"late"')
        if target == "postgres"
        else ('`s0`.`text ``"é`', "`late`")
    )
    assert (
        f"(CASE WHEN ({field} IS NOT NULL) THEN (CASE WHEN ({field} < {field}) "
        f"THEN {field} ELSE {field} END) ELSE {field} END) AS {late}"
    ).encode() in sql
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    assert [(item["label"], item["nullable"]) for item in document["columns"]] == [
        ("id", False),
        ("hi", False),
        ("word", True),
        ("top", False),
        ("low", False),
        ("late", True),
    ]
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(value.value for value in outcome.artifact.fixed_values)
    assert emit_compiled(loaded, values).rendered.sql == sql
    assert prepare_live_template(outcome.artifact).artifact.rendered.sql == sql
    flags = "table result:\n    from rows\n    select:\n        id\n        v = min(flag, flag)\n"
    _, blocked = emission.build_case(tmp_path / "bool", header + flags, encoded)
    assert blocked.status == "BLOCKED" and blocked.artifact is None
    assert [(item.code, item.detail) for item in blocked.blockers] == [
        ("PIE-B1003", "comparison_type_pair_not_admitted")
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_max_and_min_of_two_timestamps_or_uuids_emit_replay_and_bind(tmp_path, target):
    """Timestamp and UUID values order as their project comparison does, so
    their `max` and `min` are one emitted, compiled-replay and live-template
    statement on both targets."""
    pg = target == "postgres"
    body = (
        "    from rows\n    select:\n        id\n"
        "        late = max(ts, ts2)\n        first = min(ts, ts)\n"
        "        key = min(u, u)\n"
    )
    checked, outcome = emission.temporal_case(tmp_path / "ok", target, body)
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    q = '"' if pg else "`"
    ts, ts2 = f"{q}s0{q}.{q}ts{q}", f"{q}s0{q}.{q}ts2{q}"
    assert (
        f"(CASE WHEN ({ts2} IS NOT NULL) THEN (CASE WHEN ({ts} < {ts2}) "
        f"THEN {ts2} ELSE {ts} END) ELSE {ts2} END) AS {q}late{q}"
    ).encode() in sql
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    assert [(item["label"], item["nullable"]) for item in document["columns"]] == [
        ("id", False),
        ("late", True),
        ("first", False),
        ("key", False),
    ]
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(value.value for value in outcome.artifact.fixed_values)
    assert emit_compiled(loaded, values).rendered.sql == sql
    assert prepare_live_template(outcome.artifact).artifact.rendered.sql == sql


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_max_and_min_of_two_dates_emit_replay_and_bind_on_postgresql(tmp_path, target):
    """On PostgreSQL two Date values of one carrier order as their project
    comparison does, so their `max` and `min` are the conditional of the other
    types, emitted, replayed from compiled input and bound by a live template.
    MySQL keeps the conditional refused until its own differential."""
    body = "    from rows\n    select:\n        id\n        v = max(d, d2)\n"
    if target == "mysql":
        _, blocked = emission.temporal_case(tmp_path, target, body)
        assert blocked.status == "BLOCKED" and blocked.artifact is None
        assert [(item.code, item.detail) for item in blocked.blockers] == [
            ("PIE-B1003", "conditional_realization_not_admitted")
        ]
        return
    checked, outcome = emission.temporal_case(
        tmp_path, target, body + "        w = min(d2, d)\n"
    )
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    d, d2 = '"s0"."d"', '"s0"."d2"'
    assert (
        f"(CASE WHEN ({d2} IS NOT NULL) THEN (CASE WHEN ({d} < {d2}) "
        f'THEN {d2} ELSE {d} END) ELSE {d2} END) AS "v", '
        f"(CASE WHEN ({d} IS NOT NULL) THEN (CASE WHEN ({d2} > {d}) "
        f'THEN {d} ELSE {d2} END) ELSE {d} END) AS "w"'
    ).encode() in sql
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    assert [
        (item["label"], item["logical_type"]["name"], item["nullable"])
        for item in document["columns"]
    ] == [("id", "Int", False), ("v", "Date", True), ("w", "Date", True)]
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(value.value for value in outcome.artifact.fixed_values)
    assert emit_compiled(loaded, values).rendered.sql == sql
    assert prepare_live_template(outcome.artifact).artifact.rendered.sql == sql


def test_a_join_of_a_conditional_query_with_a_call_in_its_aggregate_replays(
    tmp_path,
):
    """On PostgreSQL a LEFT JOIN reads a query whose WHERE calls a def that
    inlines to a conditional and counts `lower` of the joined label; under
    bind-safe literals the compiled replay and the live template render the
    emitted SQL, its four slots in rendered order."""
    body = (
        "query pred:\n    from rhs\n    where band(id) == 2\n"
        "    select:\n        id\n        label\n"
        "query result:\n    from lhs\n    let r = pred\n"
        "    left join r on lhs.id == r.id\n    group by lhs.id\n"
        "    select:\n        a = lhs.id\n        n = count(lower(r.label))\n"
    )
    item = emission.labelled_join_witness("postgres", body, policy="bind_safe_literals")
    checked, outcome = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    assert (
        b'WHERE ((CASE WHEN ("s0"."order.id" <= CAST($1 AS pg_catalog.int8)) '
        b"THEN CAST($2 AS pg_catalog.int8) ELSE CAST($3 AS pg_catalog.int8) END) "
        b"= CAST($4 AS pg_catalog.int8))"
    ) in sql
    assert b' LEFT JOIN "p1" AS "m1" ' in sql
    assert b'COUNT(lower("t0"."c4")) AS "c1"' in sql
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(value.value for value in outcome.artifact.fixed_values)
    assert values == (1, 3, 2, 2)
    assert emit_compiled(loaded, values).rendered.sql == sql
    assert prepare_live_template(outcome.artifact).artifact.rendered.sql == sql


@pytest.mark.parametrize(
    "source",
    (rows.CANONICAL, rows.HEAD + rows.GROUPED, rows.IMPORTED),
    ids=("left", "grouped", "imported"),
)
def test_a_relationship_over_query_rows_replays_as_its_written_on(tmp_path, source):
    """A query's rows passed to a relationship, on the LEFT side, as a
    grouped query keyed by its GROUP BY key (B14) or imported from another
    module, emit the bytes of the same `on` written out; the compiled replay
    and the live template keep them."""
    imported = isinstance(source, dict)
    contract = rows.project_contract(
        customers="rows.pietto" if imported else "main.pietto"
    )
    checked, outcome = emission.build_case(tmp_path / "call", source, contract)
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    _, written = emission.build_case(
        tmp_path / "written",
        {path: rows.written_on(text) for path, text in source.items()}
        if imported
        else rows.written_on(source),
        contract,
    )
    assert written.artifact is not None and written.artifact.rendered.sql == sql
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(value.value for value in outcome.artifact.fixed_values)
    assert emit_compiled(loaded, values).rendered.sql == sql
    assert prepare_live_template(outcome.artifact).artifact.rendered.sql == sql


@pytest.mark.parametrize(
    "expression,precision",
    [
        ("money * id", 28),
        ("id * money", 28),
        ("money * 2", 28),
        ("-money", 9),
        ("+money", 9),
        ("-(money * id)", 28),
    ],
)
def test_decimal_multiply_and_sign_close_project_readers(
    tmp_path, expression, precision
):
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    body = f"table result:\n    from rows\n    select:\n        result = {expression}\n"
    item = emission.parameterized_fixture("postgres", body, protocol=False)
    checked, outcome = emission.build_case(tmp_path, item["source"], item["contract"])
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    document = emission.decode_public(serialize_project_sql_emission(outcome))
    storage = document["columns"][0]["representation"]["storage"]
    assert storage == {"kind": "pg_numeric", "precision": precision, "scale": 2}
    observation = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    )
    assert observation.status is portable.ObservationStatus.OK
    assert observation.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observation.canonical_bytes).status
        is pure.Status.OK
    )
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, ())
    assert replay.rendered.sql == outcome.artifact.rendered.sql


def test_mysql_compiled_aggregate_scalar_keeps_two_query_boundary(tmp_path):
    from dataclasses import replace
    from pietto._project.project_compiled_schema import FIELDS, CompiledError, Record
    from pietto._project.project_compiled_verification import verify_description

    item = emission.aggregate_fixture("mysql", "X_aggregate_global", "bag")
    source = item["source"].split("query result:", 1)[0] + (
        "table totals:\n    from agg\n    select:\n        total = min(value)\n"
        "query result:\n    from totals\n    select:\n        result = coalesce(total, 0)\n"
    )
    checked, outcome = emission.build_case(tmp_path, source, item["contract"])
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql == artifact.rendered.sql
    records = built.root.records
    aggregate = next(
        record for record in records.values() if record.address.kind == "aggregate"
    )
    projection = next(
        record
        for record in records.values()
        if record.address.kind == "row"
        and record.get("stage") == "projection"
        and any(value.kind == "operation" for value in record.get("values"))
    )
    assert projection.get("owner") != aggregate.get("owner")
    values = list(projection.values)
    values[FIELDS["row"].index("owner")] = aggregate.get("owner")
    forged = Record(projection.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (
                name,
                tuple(
                    forged if record.address == forged.address else record
                    for record in members
                ),
            )
            for name, members in built.root.description.members
        ),
    )
    with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_COMPOSITION_TARGET$"):
        verify_description(description)


@pytest.mark.parametrize(
    "expression", ("Float(total)", "total if n > 0 else 0", "total > 0")
)
def test_compiled_aggregate_composition_keeps_two_query_expression_boundaries(
    tmp_path, expression
):
    from dataclasses import replace
    from pietto._project.project_compiled_schema import FIELDS, CompiledError, Record
    from pietto._project.project_compiled_verification import verify_description

    item = emission.aggregate_fixture("postgres", "X_aggregate_global", "bag")
    source = item["source"].split("query result:", 1)[0] + (
        "table totals:\n    from agg\n    select:\n        total = sum(value)\n        n = count()\n"
        "query result:\n    from totals\n    select:\n"
        f"        result = {expression}\n"
    )
    checked, outcome = emission.build_case(tmp_path, source, item["contract"])
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql == artifact.rendered.sql
    records = built.root.records
    aggregate = next(
        record for record in records.values() if record.address.kind == "aggregate"
    )
    projection = next(
        record
        for record in records.values()
        if record.address.kind == "row"
        and record.get("stage") == "projection"
        and any(value.kind == "operation" for value in record.get("values"))
    )
    assert projection.get("owner") != aggregate.get("owner")
    values = list(projection.values)
    values[FIELDS["row"].index("owner")] = aggregate.get("owner")
    forged = Record(projection.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (
                name,
                tuple(
                    forged if record.address == forged.address else record
                    for record in members
                ),
            )
            for name, members in built.root.description.members
        ),
    )
    with pytest.raises(
        CompiledError, match="^COMPILED_AGGREGATE_COMPOSITION_EXPRESSION$"
    ):
        verify_description(description)
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    data = portable.export_emission_observation(
        artifact, artifact.request
    ).canonical_bytes
    assert (
        data is not None
        and pure.parse_emission_observation(data).status is pure.Status.OK
    )
    document = json.loads(data)
    bodies = [
        record["fields"]
        for record in document["records"]
        if record["ref"][0] == "row_body"
    ]
    aggregate_body = next(body for body in bodies if body["aggregation"] is not None)
    projection_body = next(
        body
        for body in bodies
        if body["block_kind"] == "projection"
        and any(column[0] == "row_value_column" for column in body["columns"])
    )
    assert projection_body["definition"] != aggregate_body["definition"]
    projection_body["definition"] = aggregate_body["definition"]
    refused = pure.parse_emission_observation(json.dumps(document))
    assert refused.status is pure.Status.INVALID_RELATION
    assert refused.detail == "aggregate composition expression"


@pytest.mark.parametrize("expression", ("1", "1 + 2"))
def test_compiled_global_aggregate_rejects_zero_leaf_projection(tmp_path, expression):
    from dataclasses import replace
    from pietto._project.project_compiled_schema import FIELDS, CompiledError, Record
    from pietto._project.project_compiled_verification import verify_description

    item = emission.aggregate_fixture("postgres", "X_aggregate_global", "bag")
    source = item["source"].split("query result:", 1)[0] + (
        "table totals:\n    from agg\n    select:\n        n = count()\n"
        "query result:\n    from totals\n    select:\n"
        f"        fixed = {expression}\n"
    )
    checked, outcome = emission.build_case(tmp_path, source, item["contract"])
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql == artifact.rendered.sql
    aggregate = next(
        record
        for record in built.root.records.values()
        if record.address.kind == "aggregate"
    )
    projection = next(
        record
        for record in built.root.records.values()
        if record.address.kind == "row"
        and record.get("stage") == "projection"
        and any(value.kind != "read" for value in record.get("values"))
    )
    values = list(projection.values)
    values[FIELDS["row"].index("owner")] = aggregate.get("owner")
    forged = Record(projection.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (
                name,
                tuple(
                    forged if record.address == forged.address else record
                    for record in members
                ),
            )
            for name, members in built.root.description.members
        ),
    )
    with pytest.raises(
        CompiledError, match="^COMPILED_GLOBAL_AGGREGATE_COMPOSITION_LEAF$"
    ):
        verify_description(description)


TEXT_WINDOW_DEFAULT_BODY = """query result:
    from rows
    select:
        id
        previous = lag(text, 1, "雪") window(order by id)
        following = lead(text, 1, "a'b") window(order by id)
"""


FLOAT_REMAINDER_BODY = """query result:
    from rows
    select:
        id
        remainder = ratio % 0.1
"""


FLOAT_FIELD_ARITHMETIC_BODY = """query result:
    from rows
    where ratio * 2.0 > 1.0
    select:
        id
        doubled = ratio * 2.0
        summed = ratio + ratio
        negated = -ratio
        nested = ratio - ratio * ratio
        folded = 1.5 + 2.25
"""


TARGETS = ("postgres", "mysql")


def emit(tmp_path, target, body):
    item = probe.parameterized_fixture(
        target, body, "preserve_literals", protocol=False
    )
    return probe.build_case(
        tmp_path, item["source"], item["contract"], "preserve_literals"
    )


def emit_source(tmp_path, target, body):
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    contract = json.loads(item["contract"])
    header = probe.AGGREGATE_HEADER.format(target=target)
    _, outcome = probe.build_case(
        tmp_path, header + body, probe.encoded(contract).decode(), "preserve_literals"
    )
    return outcome


def row_query(artifact):
    query = artifact.ast
    assert isinstance(query, SQLRowQuery)
    return query


def public(outcome) -> dict[str, Any]:
    """The independent consumer's verdict over the published bytes alone."""
    return probe.decode_public(serialize_project_sql_emission(outcome))


def test_postgres_decimal_carriers_emit_exact_addition(tmp_path):
    checked, outcome = emit(tmp_path, "postgres", S05_POSTGRES_BODY)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    assert "pg_catalog.numeric(22, 2)" in document["sql"]
    assert "pg_catalog.numeric(10, 2)" in document["sql"]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    )
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )

    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).request.family == "postgres"


@pytest.mark.parametrize("target", TARGETS)
def test_postgres_text_window_defaults_are_escaped_and_widen_the_result(
    tmp_path, target
):
    """E7 opens only static Text literals beside Text lag/lead values."""
    checked, outcome = emit(tmp_path, target, TEXT_WINDOW_DEFAULT_BODY)
    assert checked.verified
    if target == "mysql":
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert [(blocker.code, blocker.detail) for blocker in outcome.blockers] == [
            ("PIE-B1003", "window_default_literal_kind_not_realized_yet"),
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql.decode("utf-8")
    assert "E'\\351\\233\\252'" in sql
    assert "E'\\141\\047\\142'" in sql
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    defaults = [
        column["representation"]["domain"]["max_characters"]
        for column in document["columns"]
        if column["label"] in {"previous", "following"}
    ]
    assert len(defaults) == 2 and min(defaults) >= 3
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
    )

    built = build_compiled(artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == artifact.rendered.sql


@pytest.mark.parametrize("target", TARGETS)
def test_postgres_float_remainder_uses_the_exact_binary64_lowering(tmp_path, target):
    """E5 admits same-type Float `%` only through the PostgreSQL exact path."""
    checked, outcome = emit(tmp_path, target, FLOAT_REMAINDER_BODY)
    assert checked.verified
    if target == "mysql":
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert [(blocker.code, blocker.detail) for blocker in outcome.blockers] == [
            ("PIE-B1003", "float_remainder_exact_binary64_not_realized")
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql.decode("utf-8")
    assert 'WITH "__pietto_s04_operands" AS MATERIALIZED (SELECT ' in sql
    assert "pg_catalog.float8send" in sql
    assert "pg_catalog.mod" in sql
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
    )

    built = build_compiled(artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == artifact.rendered.sql


@pytest.mark.parametrize("target", TARGETS)
def test_postgres_float_field_arithmetic_rests_on_the_checked_float8_operator(
    tmp_path, target
):
    """E4: PostgreSQL emits Float `+`, `-`, `*` over a field uncast, each with
    the R05 evidence that its checked float8 operator refuses a non-finite
    result (SQLSTATE 22003), and a sign, which never fails, without it; a
    literal fold stays statically checked. The observation, the independent
    public consumer and the compiled template agree. MySQL keeps it refused."""
    checked, outcome = emit(tmp_path, target, FLOAT_FIELD_ARITHMETIC_BODY)
    assert checked.verified
    if target == "mysql":
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert [(b.code, b.detail) for b in outcome.blockers] == [
            ("PIE-B1003", "float_literal_operands_required")
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    sql = document["sql"]
    ratio = '"t1"."c4"'
    for spelling in (
        f"({ratio} * CAST('2.0' AS pg_catalog.float8)) AS \"doubled\"",
        f'({ratio} + {ratio}) AS "summed"',
        f'(-{ratio}) AS "negated"',
        f'({ratio} - ({ratio} * {ratio})) AS "nested"',
        "(CAST('1.5' AS pg_catalog.float8) + CAST('2.25' AS pg_catalog.float8))",
    ):
        assert spelling in sql
    checked_token = {"overflow": "target_checked_binary64_overflow"}
    assert [
        r["evidence"] for r in document["requirements"] if r["kind"] == "arithmetic"
    ] == [
        [{"operator": "*"}, checked_token],
        [{"operator": "*"}, checked_token],
        [{"operator": "+"}, checked_token],
        [{"operator": "-"}],
        [{"operator": "-"}, checked_token],
        [{"operator": "*"}, checked_token],
        [{"operator": "+"}],
    ]
    assert all(
        c["representation"]["storage"] == {"kind": "pg_float8"}
        and c["representation"]["domain"]
        == {"kind": "finite_float", "format": "binary64"}
        for c in document["columns"][1:]
    )
    artifact = outcome.artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
    )

    built = build_compiled(artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == artifact.rendered.sql


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    "grouped,expression,leaf_functions",
    [
        (False, "coalesce(sum(value), 0)", ("sum",)),
        (False, "sum(value) + sum(value)", ("sum", "sum")),
        (False, "sum(value) * 100 / count()", ("sum", "count")),
        (False, "abs(min(value))", ("min",)),
        (False, "abs(avg(value))", ("avg",)),
        pytest.param(False, "avg(value) / 2.0", ("avg",), id="float_division"),
        pytest.param(
            False, "sum(value) % count()", ("sum", "count"), id="int_remainder"
        ),
        (False, "abs(max(amount))", ("max",)),
        (False, "coalesce(min(amount), max(amount))", ("min", "max")),
        (True, "coalesce(sum(value), 0) + coalesce(key, 0)", ("sum",)),
        (True, "coalesce(key, 0) + 1", ()),
        pytest.param(True, "1 + 2", (), id="grouped_constant"),
    ],
)
def test_aggregate_composition_preserves_leaf_ports_and_closes_readers(
    tmp_path, policy, grouped, expression, leaf_functions
):
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    body = "query result:\n    from agg\n"
    if grouped:
        body += "    group by:\n        key\n"
    body += f"    select:\n        result = {expression}\n        direct = count()\n"
    checked, outcome = emit_aggregate_composition(tmp_path, body, policy=policy)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    aggregate_columns = [
        column
        for stage in row_query(artifact).bodies
        for column in stage.columns
        if type(column) is grouping.AggregateValueColumn
    ]
    assert tuple(column.function for column in aggregate_columns) == (
        *leaf_functions,
        "count",
    )
    assert len(
        {id(column.aggregate.source.call) for column in aggregate_columns}
    ) == len(aggregate_columns)
    for column in aggregate_columns:
        if column.function == "sum":
            assert column.column.realization.nullable is True
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    if expression == "coalesce(sum(value), 0)":
        assert document["columns"][0]["nullable"] is False
    observation = portable.export_emission_observation(artifact, artifact.request)
    assert observation.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observation.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observation.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(
        loaded, tuple(value.value for value in artifact.fixed_values)
    )
    assert replay.rendered.sql == artifact.rendered.sql
    from pietto._project.project_result_output import prepare_output

    assert [
        (c.label, c.realization.nullable) for c in prepare_output(replay).columns
    ] == [(c.label, c.realization.nullable) for c in prepare_output(artifact).columns]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_aggregate_composition_keeps_legal_repeated_where_parameters(tmp_path, policy):
    from decimal import Decimal
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result(floor: Decimal(9, 2)):\n    from agg\n"
        "    where amount >= floor or amount <= floor\n"
        "    select:\n        result = coalesce(min(amount), max(amount))\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [
        (u["owner"]["parameter"], u["server_index"], u["physical_type"])
        for u in document["parameter_uses"]
    ] == [(0, 1, "pg_numeric")] * 2
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OUTSIDE_SCHEMA
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, (), (Decimal("1.25"),))
    assert replay.rendered.sql == artifact.rendered.sql
    assert len(replay.parameter_uses) == 2
    with pytest.raises(CompiledError, match="COMPILED_BINDING_PARAMETERS"):
        emit_compiled(loaded, (), (Decimal("1.234"),))

    from pietto._project.project_compiled_schema import FIELDS, Record
    from pietto._project.project_compiled_verification import verify_description

    records = built.root.records
    projection = next(
        record
        for record in records.values()
        if record.address.kind == "row" and record.get("stage") == "projection"
    )
    operation = records[projection.get("values")[0]]
    parameter = next(address for address in records if address.kind == "parameter_read")
    values = list(operation.values)
    values[FIELDS["operation"].index("operands")] = (
        operation.get("operands")[0],
        parameter,
    )
    forged = Record(operation.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (
                name,
                tuple(
                    forged if record.address == forged.address else record
                    for record in members
                ),
            )
            for name, members in built.root.description.members
        ),
    )
    with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_PARAMETER_POSITION$"):
        verify_description(description)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("ordering", ("total", "total desc"))
def test_aggregate_composition_having_alias_and_order_close_readers(
    tmp_path, policy, ordering
):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_result_output import prepare_output

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    where rid > 0\n"
        "    group by key\n    select:\n"
        "        total = coalesce(sum(value), 0)\n        raw = sum(value)\n"
        "    having total > 0 and total < 10\n"
        f"    order by {ordering}\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [column["nullable"] for column in document["columns"]] == [False, True]
    from pietto._project.project_sql_plan import ProjectSQLPlan

    assert isinstance(checked.plan, ProjectSQLPlan)
    assert len(checked.plan.aggregates) == 2
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observation = portable.export_emission_observation(artifact, artifact.request)
    assert observation.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observation.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observation.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(
        loaded, tuple(value.value for value in artifact.fixed_values)
    )
    assert replay.rendered.sql == artifact.rendered.sql
    assert [
        column.realization.nullable for column in prepare_output(replay).columns
    ] == [False, True]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("grouped", (False, True))
def test_aggregate_composition_join_keeps_each_leaf_and_original_input_port(
    tmp_path, policy, grouped
):
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project.project_sql_plan_aggregation import aggregate_call
    from pietto._project.project_sql_emission_ast import SQLJoinQuery
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    body = (
        "query result:\n    from agg\n    let rhs = agg\n"
        "    inner join rhs on agg.rid == rhs.rid\n"
        + ("    group by agg.key\n" if grouped else "")
        + "    select:\n"
        + ("        bucket = coalesce(agg.key, 0)\n" if grouped else "")
        + "        total = coalesce(sum(rhs.value), 0) + coalesce(sum(rhs.value), 0)\n"
        "        raw = sum(agg.value)\n        n = count()\n"
        + (
            "    having total > 0 and total < 100\n    order by total\n"
            if grouped
            else ""
        )
    )
    checked, outcome = emit_aggregate_composition(tmp_path, body, policy=policy)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None and isinstance(artifact.ast, SQLJoinQuery)
    values = [
        column
        for stage in artifact.ast.bodies
        for column in stage.columns
        if type(column) is grouping.AggregateValueColumn
    ]
    assert tuple(column.function for column in values) == ("sum", "sum", "sum", "count")
    assert len({id(aggregate_call(column.aggregate.source)) for column in values}) == 4
    assert values[0].argument.port is values[1].argument.port
    assert values[0].argument.port is not values[2].argument.port
    assert all(column.column.realization.nullable is True for column in values[:3])
    probe.decode_public(serialize_project_sql_emission(outcome))
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert (
        emit_compiled(
            loaded, tuple(value.value for value in artifact.fixed_values)
        ).rendered.sql
        == artifact.rendered.sql
    )


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    "expression,precision",
    (
        ("min(amount) + 1", 10),
        ("max(amount) - 1", 10),
        ("sum(amount) + 1", 29),
        ("min(amount) * 2", 28),
        ("sum(amount) * 2", 47),
        ("abs(sum(amount)) + 1", 29),
        ("-sum(amount)", 28),
        ("abs(sum(amount))", 28),
    ),
)
def test_decimal_aggregate_result_carriers_close_readers(
    tmp_path, policy, expression, precision
):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        f"query result:\n    from agg\n    select:\n        result = {expression}\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["columns"][0]["representation"]["storage"] == {
        "kind": "pg_numeric",
        "precision": precision,
        "scale": 2,
    }
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert (
        emit_compiled(
            loaded, tuple(value.value for value in artifact.fixed_values)
        ).rendered.sql
        == artifact.rendered.sql
    )


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_composition_having_keeps_one_authored_literal_value(tmp_path, policy):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    where rid > 0\n    group by key\n"
        "    select:\n        total = sum(value) + 1\n        extra = 1\n"
        "    having total > 0 and total < 100\n    order by total\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    probe.decode_public(serialize_project_sql_emission(outcome))
    defaults = tuple(value.value for value in artifact.fixed_values)
    assert defaults == ((0, 1) if policy == "bind_safe_literals" else ())
    if policy == "bind_safe_literals":
        from pietto._project.project_sql_emission_verification import (
            _active_specialized_literal,
        )

        plan = artifact.request.plan
        shared = next(
            site.position.literal
            for site in plan.literal_sites
            if site.position.role.value == "select"
            and site.position.literal.value == 1
            and site.reason is not None
            and site.reason.value == "specialized_or_structural_context"
        )
        assert _active_specialized_literal(plan, artifact.request.layout, shared)
        inactive = graft(
            plan,
            filters=tuple(
                item for item in plan.filters if item.site.role.value != "satisfying"
            ),
        )
        assert inactive.literal_sites is plan.literal_sites
        assert not _active_specialized_literal(
            inactive, artifact.request.layout, shared
        )
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, defaults).rendered.sql == artifact.rendered.sql
    if defaults:
        rebound = emit_compiled(loaded, (0, 7))
        assert rebound.rendered.sql == artifact.rendered.sql
        assert tuple(value.value for value in rebound.fixed_values) == (0, 7)


def test_postgres_string_agg_orders_by_a_float_key(tmp_path):
    """E6: a Float string_agg order key compares as a PostgreSQL Float group
    key does, by real value with -0.0 and 0.0 tied; the compiled template keeps
    it. (MySQL has no project string_agg.)"""
    outcome = emit_source(
        tmp_path,
        "postgres",
        "table result:\n    from agg\n    select:\n"
        '        summary = string_agg(label, "//", order by ratio desc, rid)\n',
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    sql = public(outcome)["sql"]
    assert ' ORDER BY "s0"."ratio value" DESC, "s0"."row id" ASC)' in sql

    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql == outcome.artifact.rendered.sql


# Phase77 Wave A (S16, S10): a MySQL project emits a lag/lead Text literal
# default, or a conditional count and tests of a group, only in a statement that
# is one of its slice's paired qualification-pack forms with only its names
# changed; everything else keeps its 0.1.11 output.
_LONG = {key: (value + "_" * 63)[:63] for key, value in paired_forms.NAMES.items()}
_LONG_COLUMNS = tuple(f"c{i}" + "_" * 61 for i in range(7))
_S10_KEPT = [
    ("PIE-B1003", "conditional_count_not_admitted_on_target"),
    ("PIE-B1003", "group_test_not_admitted_on_target"),
    ("PIE-B1003", "group_test_not_admitted_on_target"),
]


def _kept(form):
    if form in paired_forms.S16:
        return [("PIE-B1003", "window_default_literal_kind_not_realized_yet")]
    return _S10_KEPT


def _paired_compile(directory, *, name="q16", policy="preserve", kind="query"):
    from pietto.compiler import compile_sql

    return compile_sql(
        str(directory),
        module="main.pietto",
        kind=kind,
        name=name,
        dialect="mysql",
        emission_contract="contract.json",
        literal_policy=policy,
    )


def _paired_query(directory, name="q16"):
    from pietto.execution import compile_query

    return compile_query(
        directory,
        module="main.pietto",
        kind="query",
        name=name,
        dialect="mysql",
        emission_contract="contract.json",
    )


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fixed(form):
    """The keywords of form ``form``'s slice."""
    (fixed,) = (fixed for forms, fixed in pairing.SLICES if form in forms)
    return fixed


@pytest.mark.parametrize("form", range(len(paired_forms.FORMS)))
@pytest.mark.parametrize("width", ("pack", "short", "long"))
def test_mysql_emits_the_paired_forms(tmp_path, form, width):
    """Each digest the readers compare is recomputed from the pack's text;
    each form emits with the pack's own Pietto names (S10's shape and source
    are equal ignoring case) and with others."""
    from pietto.execution import export_bundle, load_bundle

    text = pairing.project_text(
        "main.pietto",
        paired_forms.pack(form),
        json.dumps(paired_forms.contract(form)),
        ("result", "query"),
        pairing._Names(),
        _fixed(form),
    )
    assert _sha(text) == pairing.FORMS[form][0]
    names, physical = (
        ({name: name for name in paired_forms.NAMES}, paired_forms.physical_names(form))
        if width == "pack"
        else (paired_forms.NAMES, paired_forms.physical_names(form))
        if width == "short"
        else (
            _LONG,
            paired_forms.physical_names(form, "n" * 63, "t" * 63, _LONG_COLUMNS),
        )
    )
    locator = "app.items" if width == "short" else "s" * 63 + "." + "t" * 63
    directory = paired_forms.project(
        tmp_path / "p", form, names=names, locator=locator, physical=physical
    )
    if width == "long":
        # As `pietto fmt` writes it: an empty line between declarations.
        main = directory / "main.pietto"
        text = main.read_text(encoding="utf-8")
        # A carriage return unpairs a file, so Windows must not write one.
        main.write_text(
            text.replace("\nsource", "\n\nsource").replace("\nquery", "\n\nquery"),
            encoding="utf-8",
            newline="\n",
        )
    result = _paired_compile(directory, name=names["result"])
    assert result.status == "VERIFIED", result.document
    document = json.loads(result.document)
    sql = document["sql"]
    world = paired_forms.WORLDS[paired_forms.FORMS[form][0]]
    columns = dict(zip((field[0] for field in world[2]), physical[2]))
    assert all(token.format_map(columns) in sql for token in paired_forms.SQL[form])
    assert "E'" not in sql
    assert [c["nullable"] for c in document["columns"]] == paired_forms.NULLABLE[form]
    # A conditional count is a BIGINT, a test of a group a computed signed Bool;
    # a lag/lead and a group key keep the value's carrier.
    assert [c["representation"]["storage"] for c in document["columns"]] == [
        {"kind": "my_signed_bool"}
        if logical == "Bool"
        else paired_forms.STORAGE[logical][0]
        for logical in paired_forms.LOGICAL[form]
    ]
    assert _sha(pairing.sql_text(sql.encode())) == pairing.FORMS[form][1]
    bundle = export_bundle(_paired_query(directory, names["result"]))
    records = {r.address: r for r in compiled_schema.decode(bundle.payload).records}
    assert (
        _sha(pairing.compiled_text(records, pairing._Names())),
        len(records),
    ) == pairing.FORMS[form][2:]
    loaded = load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert loaded._template.artifact.rendered.sql.decode() == sql


def test_paired_forms_keep_each_keyword_apart_from_names():
    """A slice's keywords are exactly the words of its forms that are no
    names: another word in a keyword's place gives another reduction."""
    for forms, fixed in pairing.SLICES:
        seen = set()
        for form in forms:
            text = paired_forms.pack(form)
            reduced = pairing._module(text, pairing._Names(), fixed)
            words = {
                match[0]
                for match in pairing._TOKEN.finditer(text)
                if match[1] is None and match[0][0] != '"'
            } - set(paired_forms.NAMES)
            for word in words:
                other = re.sub(rf"\b{word}\b", "zz", text)
                reduction = pairing._module(other, pairing._Names(), fixed)
                assert reduction != reduced, (form, word)
            seen |= words
        assert seen == fixed


@pytest.mark.parametrize(
    "form,key,word",
    (
        *((1, "previous", word) for word in ("sum", "all", "any", "unique")),
        (1, "text", "group"),
        *((3, "n", word) for word in ("lag", "lead", "order")),
        (3, "value", "lag"),
    ),
)
def test_mysql_forms_take_another_slice_keywords_as_names(tmp_path, form, key, word):
    """One slice's keywords stay names in another's forms: a label or field so
    named still pairs."""
    names = dict(paired_forms.NAMES, **{key: word})
    directory = paired_forms.project(tmp_path / "p", form, names=names)
    result = _paired_compile(directory)
    assert result.status == "VERIFIED", result.document


def _swap(text, old, new):
    assert text.count(old) >= 1
    return text.replace(old, new)


_UNPAIRED = {
    "non_ascii_column": (1, lambda t: t, {"contract": ("column", "c_bödy")}),
    # Letters that fold to ASCII ones ignoring case: Kelvin sign, long s, i.
    "kelvin_column": (1, lambda t: t, {"contract": ("column", "c_\u212a")}),
    "kelvin_locator": (1, lambda t: _swap(t, '"app.', '"\u212aapp.'), None),
    "long_s_locator": (1, lambda t: _swap(t, '"app.', '"\u017fapp.'), None),
    "dotless_i_locator": (1, lambda t: _swap(t, '.items"', '.\u0131tems"'), None),
    "long_label": (1, lambda t: _swap(t, "prv", "p" * 64), None),
    "pietto_prefix": (1, lambda t: _swap(t, "prv", "__PIETTO_prv"), None),
    "case_twin_labels": (0, lambda t: _swap(t, "fu =", "PE ="), None),
    "one_part_locator": (1, lambda t: _swap(t, '"app.items"', '"items"'), None),
    "three_part_locator": (1, lambda t: _swap(t, '"app.items"', '"a.b.items"'), None),
    "other_default": (1, lambda t: _swap(t, '"雪"', '"雨"'), None),
    "wider_default": (1, lambda t: _swap(t, '"雪"', '"雪雪"'), None),
    "swapped_functions": (
        1,
        lambda t: _swap(_swap(_swap(t, "lag(", "@("), "lead(", "lag("), "@(", "lead("),
        None,
    ),
    "offset_two": (
        1,
        lambda t: _swap(t, 'lag(body, 1, "雪")', 'lag(body, 2, "雪")'),
        None,
    ),
    "descending": (
        1,
        lambda t: _swap(t, "(order by k)\n", "(order by k desc)\n"),
        None,
    ),
    "extra_item": (
        1,
        lambda t: t + "        again = lead(body, 1) window(order by k)\n",
        None,
    ),
    "dropped_item": (1, lambda t: t[: t.index("        fol =")], None),
    "reordered_items": (
        1,
        lambda t: _swap(
            t,
            '        prv = lag(body, 1, "雪") window(order by k)\n'
            '        fol = lead(body, 1, "a\'b") window(order by k)\n',
            '        fol = lead(body, 1, "a\'b") window(order by k)\n'
            '        prv = lag(body, 1, "雪") window(order by k)\n',
        ),
        None,
    ),
    "comment": (1, lambda t: _swap(t, "query q16:\n", "# note\nquery q16:\n"), None),
    "spaces_only_line": (1, lambda t: _swap(t, "query q16:", "    \nquery q16:"), None),
    "trailing_space": (
        1,
        lambda t: _swap(t, "    from items\n", "    from items \n"),
        None,
    ),
    "extra_query": (
        1,
        lambda t: t + "\nquery other:\n    from items\n    select:\n        k\n",
        None,
    ),
    "type_alias": (
        1,
        lambda t: "type Key = Int\n" + _swap(t, "    k: Int\n", "    k: Key\n"),
        None,
    ),
    "table_kind": (
        1,
        lambda t: _swap(t, "query q16:", "table q16:"),
        {"kind": "table"},
    ),
    "bind_safe": (1, lambda t: t, {"policy": "bind-safe"}),
    "second_module": (
        1,
        lambda t: t,
        {"module": 'shape S:\n    a: Int\n\nsource s: S = mysql.table("app.s")\n'},
    ),
    "contract_width": (1, lambda t: t, {"contract": ("max_characters", 32)}),
    "contract_premise": (1, lambda t: t, {"contract": ("premise", None)}),
    "contract_order": (1, lambda t: t, {"contract": ("order", None)}),
}


_S10_GROUP_BY = "    group by:\n        bucket\n"
_S10_ITEMS = (
    "        cnt = sum(1 for e in group if e.f)\n",
    "        every_f = all(e.f for e in group)\n",
    '        some_tag = any(e.tag == "a" for e in group)\n',
)
_UNPAIRED.update(
    {
        "s10_other_literal": (3, lambda t: _swap(t, '"a"', '"b"'), None),
        "s10_wider_literal": (3, lambda t: _swap(t, '"a"', '"ab"'), None),
        "s10_swapped_tests": (
            3,
            lambda t: _swap(
                _swap(_swap(t, "all(", "@("), "any(", "all("), "@(", "any("
            ),
            None,
        ),
        "s10_negated_count": (3, lambda t: _swap(t, "if e.f)", "if not e.f)"), None),
        "s10_other_count_test": (
            3,
            lambda t: _swap(t, "if e.f)", 'if e.tag == "a")'),
            None,
        ),
        "s10_swapped_operands": (
            3,
            lambda t: _swap(t, 'e.tag == "a"', '"a" == e.tag'),
            None,
        ),
        # Not a conditional count: check refuses it (PIE-S2315).
        "s10_count_two": (
            3,
            lambda t: _swap(t, "sum(1 for", "sum(2 for"),
            {"blockers": []},
        ),
        "s10_other_key": (
            3,
            lambda t: _swap(t, _S10_GROUP_BY, "    group by:\n        qty\n"),
            None,
        ),
        "s10_extra_key": (
            3,
            lambda t: _swap(t, _S10_GROUP_BY, _S10_GROUP_BY + "        qty\n"),
            None,
        ),
        "s10_where": (
            3,
            lambda t: _swap(
                t,
                "    from entry\n",
                "    from entry\n    where:\n        row_no > 1\n",
            ),
            None,
        ),
        "s10_dropped_item": (
            3,
            lambda t: _swap(t, _S10_ITEMS[2], ""),
            {"blockers": _S10_KEPT[:2]},
        ),
        "s10_extra_item": (
            3,
            lambda t: t + "        again = sum(1 for e in group if e.f)\n",
            {"blockers": [*_S10_KEPT, _S10_KEPT[0]]},
        ),
        "s10_reordered_items": (
            3,
            lambda t: _swap(
                t, _S10_ITEMS[0] + _S10_ITEMS[1], _S10_ITEMS[1] + _S10_ITEMS[0]
            ),
            {"blockers": [_S10_KEPT[1], _S10_KEPT[0], _S10_KEPT[2]]},
        ),
        "s10_two_members": (
            3,
            lambda t: _swap(t, "all(e.f for e in group)", "all(x.f for x in group)"),
            None,
        ),
        "s10_keyword_label": (3, lambda t: _swap(t, "cnt =", "sum ="), None),
        "s10_case_twin_labels": (3, lambda t: _swap(t, "every_f =", "CNT ="), None),
        # The form's shape and source are equal ignoring case; these are not.
        "s10_untwinned_names": (3, lambda t: t.replace("Entry", "Bucket"), None),
        "s10_nullable_label": (
            3,
            lambda t: _swap(t, "    tag: Text\n", "    tag: Text | None\n"),
            {"contract": ("nullable", 3)},
        ),
        "s10_no_unique": (
            3,
            lambda t: _swap(t, "    entry_key = unique(row_no)\n", ""),
            None,
        ),
        "s10_kelvin_column": (3, lambda t: t, {"contract": ("column", "c_K")}),
        "s10_table_kind": (
            3,
            lambda t: _swap(t, "query q16:", "table q16:"),
            {"kind": "table"},
        ),
        "s10_bind_safe": (4, lambda t: t, {"policy": "bind-safe"}),
        "s10_extra_query": (
            5,
            lambda t: (
                t + "\nquery other:\n    from entry\n    select:\n        row_no\n"
            ),
            None,
        ),
    }
)


@pytest.mark.parametrize("case", sorted(_UNPAIRED))
def test_mysql_unpaired_statements_keep_the_main_output(tmp_path, case):
    """Every other statement reports its whole output from before Wave A."""
    form, edit, options = _UNPAIRED[case]
    options = options or {}
    directory = paired_forms.project(tmp_path / "p", form)
    main = directory / "main.pietto"
    main.write_text(
        edit(main.read_text(encoding="utf-8")), encoding="utf-8", newline="\n"
    )
    if "module" in options:
        (directory / "other.pietto").write_text(options["module"], newline="\n")
    if "contract" in options:
        contract = json.loads((directory / "contract.json").read_text())
        change, value = options["contract"]
        if change == "max_characters":
            field = contract["sources"][0]["fields"][2]["representation"]
            field["domain"]["max_characters"] = value
            field["storage"]["length"] = value
        elif change == "column":
            contract["sources"][0]["fields"][2]["column"] = value
        elif change == "nullable":
            contract["sources"][0]["fields"][value]["representation"]["nullable"] = True
        elif change == "premise":
            contract["environment"].append(
                {
                    "key": "parameter_protocol",
                    "scope": "statement",
                    "value": "mysql_prepared",
                }
            )
        else:
            contract["environment"].reverse()
        (directory / "contract.json").write_text(json.dumps(contract))
    arguments = {k: v for k, v in options.items() if k in {"kind", "policy"}}
    result = _paired_compile(directory, **arguments)
    with pairing.closed():
        before = _paired_compile(directory, **arguments)
    assert result.document == before.document
    blockers = json.loads(result.document).get("blockers") or []
    assert [(b["code"], b["subject"]["detail"]) for b in blockers] == options.get(
        "blockers", _kept(form)
    )


@pytest.mark.parametrize("form", (1, 3))
def test_mysql_paired_statement_without_its_sql_keeps_the_main_output(
    tmp_path, monkeypatch, form
):
    """Rule two: a paired statement that does not end as its form's SQL, as
    here after a refused live verification or other SQL, reports the output
    it has without the pairing."""
    from pietto._project import project_sql_emission as emitting
    from pietto._project.project_sql_emission_verification import (
        EmissionVerification,
    )

    directory = paired_forms.project(tmp_path / "p", form)
    with pairing.closed():
        before = _paired_compile(directory).document
    assert [
        (b["code"], b["subject"]["detail"]) for b in json.loads(before)["blockers"]
    ] == _kept(form)
    with monkeypatch.context() as patch:
        patch.setattr(pairing, "sql_form", lambda sql: None)
        assert _paired_compile(directory).document == before
    with monkeypatch.context() as patch:
        patch.setattr(
            emitting,
            "verify_project_sql_emission",
            lambda artifact, request: EmissionVerification(("forced",)),
        )
        assert _paired_compile(directory).document == before
    assert _paired_compile(directory).status == "VERIFIED"


def test_mysql_live_verifier_pairs_the_statement_itself(tmp_path, monkeypatch):
    """A statement that emission alone takes for a form, and so emits with
    its Text defaults, is refused by the live verifier's own reading."""
    from types import SimpleNamespace

    from pietto._project import project_sql_emission_windows as windowing

    directory = paired_forms.project(tmp_path / "p", 1)
    main = directory / "main.pietto"
    main.write_text(
        _swap(main.read_text(encoding="utf-8"), '"雪"', '"雨"'),
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(
        windowing,
        "pairing",
        SimpleNamespace(
            project_form=lambda request: 1, compiled_form=pairing.compiled_form
        ),
    )
    blockers = json.loads(_paired_compile(directory).document).get("blockers")
    assert [(b["code"], b["subject"]["detail"]) for b in blockers or []] == [
        ("PIE-B1008", "plan_ast_correspondence")
    ]


def _not_from(monkeypatch, name, filename, function):
    """Make ``pairing.<name>`` find no form when ``function`` of ``filename``
    calls it, and the real one elsewhere; the list records those calls."""
    real, calls = getattr(pairing, name), []

    def reader(value):
        code = sys._getframe(1).f_code
        if code.co_name == function and code.co_filename.endswith(filename):
            calls.append(function)
            return None
        return real(value)

    monkeypatch.setattr(pairing, name, reader)
    return calls


@pytest.mark.parametrize(
    "filename,function",
    (
        ("project_sql_emission_aggregation.py", "value_column"),
        ("project_sql_emission_verification.py", "_verify_aggregate_body"),
    ),
)
def test_mysql_each_live_s10_check_pairs_the_statement_itself(
    tmp_path, monkeypatch, filename, function
):
    """Emission's and the live verifier's argument laws each read the pairing
    themselves: when one alone finds no form, the statement keeps main's
    output."""
    directory = paired_forms.project(tmp_path / "p", 3)
    with pairing.closed():
        before = _paired_compile(directory).document
    calls = _not_from(monkeypatch, "project_form", filename, function)
    assert _paired_compile(directory).document == before
    assert calls


@pytest.mark.parametrize(
    "filename,function",
    (
        ("project_completed_semantics.py", "derive_compiled_semantics"),
        ("project_sql_emission_aggregation.py", "build_compiled_stage"),
        ("project_compiled_verification.py", "verify_unit_body"),
        ("project_completed_semantics.py", "verify_compiled_semantics"),
    ),
)
def test_mysql_each_compiled_s10_check_pairs_the_bundle_itself(
    tmp_path, monkeypatch, filename, function
):
    """Each compiled check of an S10 bundle's arguments reads the pairing
    itself: when one alone finds no form, the bundle keeps main's refusal."""
    from pietto.execution import export_bundle

    bundle = export_bundle(_paired_query(paired_forms.project(tmp_path / "p", 3)))
    calls = _not_from(monkeypatch, "compiled_form", filename, function)
    assert _load_refusal(bundle, bundle.payload) == (
        "PIE-R1004",
        "COMPILED_AGGREGATE_ARGUMENT",
    )
    assert calls


# The place of the requirement origin of form 3's `mysql.table` literal.
_S10_ORIGIN = '["main.pietto",10,35,10,46]'
# A target contract's encoding as a bundle spells it, and a lone surrogate.
_ENCODING = '\\"value\\":\\"utf8mb4\\"}'
_SURROGATE = '\\"value\\":\\"\\\\ud800\\"}'


def _paired_payload(directory, old, new):
    from pietto.execution import export_bundle

    bundle = export_bundle(_paired_query(directory))
    payload = bundle.payload.replace(old.encode(), new.encode())
    assert payload != bundle.payload
    return bundle, payload


def _load_refusal(bundle, payload):
    from pietto.execution import RequestRejected, load_bundle

    with pytest.raises(RequestRejected) as rejected:
        load_bundle(
            payload,
            expected_pin=compiled_schema.content_pin(payload),
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
        )
    return rejected.value.code, rejected.value.failure.detail


@pytest.mark.parametrize(
    "form,old,new,paired",
    (
        (1, '["Text","雪"]', '["Text","雨"]', False),
        (1, '"c5"', '"c9"', False),
        (1, '"lag"', '"lead"', False),
        (1, "c_body", "c_K", False),
        # Still the form's records, but `c2` is also a name the SQL generates.
        (1, "c_body", "c2", True),
        (3, '["Text","a"]', '["Text","b"]', False),
        (3, '"group_any"', '"group_all"', False),
        (3, "c_body", "c_K", False),
        (3, "c_body", "c2", True),
        # A requirement origin without a place is no form, and one with a
        # malformed place is a form's records: main's refusal of its place.
        (3, _S10_ORIGIN, "[]", False),
        (3, _S10_ORIGIN, '["main.pietto"]', True),
        # A contract the records cannot spell in UTF-8 is no form.
        (1, _ENCODING, _SURROGATE, False),
        (3, _ENCODING, _SURROGATE, False),
    ),
)
def test_mysql_forged_paired_bundles_are_refused(tmp_path, form, old, new, paired):
    """Each keeps main's refusal of a MySQL Text default, conditional count or
    test of a group bundle, also one whose records are a form's but whose SQL
    is not or that another check refuses."""
    directory = paired_forms.project(tmp_path / "p", form)
    bundle, payload = _paired_payload(directory, old, new)
    records = {r.address: r for r in compiled_schema.decode(payload).records}
    assert (pairing.compiled_form(records) == form) is paired
    assert _load_refusal(bundle, payload) == (
        ("PIE-R1008", "COMPILED_JSON")
        if new == _SURROGATE
        else ("PIE-R1008", "COMPILED_WINDOW_STATIC")
        if form in paired_forms.S16
        else ("PIE-R1008", "COMPILED_REQUIREMENT_LOCATION")
        if old == _S10_ORIGIN
        else ("PIE-R1004", "COMPILED_AGGREGATE_ARGUMENT")
    )


def _pure_document(tmp_path, form):
    directory = paired_forms.project(tmp_path / "p", form)
    names = dict(paired_forms.NAMES, result="result")
    paired_forms.project(directory, form, names=names)
    contract = (directory / "contract.json").read_text()
    source = (directory / "main.pietto").read_text(encoding="utf-8")
    _, outcome = probe.build_case(tmp_path / "case", source, contract)
    artifact = outcome.artifact
    assert outcome.status == "VERIFIED" and artifact is not None, outcome.blockers
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    return observed.canonical_bytes


def test_pure_reads_a_mysql_lag_default_by_its_position(tmp_path):
    """The pure reader refuses a MySQL Text default, also one whose role a
    forged document relabels."""
    canonical = _pure_document(tmp_path, 1)
    genuine = pure.parse_emission_observation(canonical)
    assert (genuine.status, genuine.detail) == (
        pure.Status.INVALID_RELATION,
        "window value result representation",
    )
    document = json.loads(canonical)
    for record in document["records"]:
        if (
            record["ref"][0] == "window_argument"
            and record["fields"]["role"] == "default"
        ):
            record["fields"]["role"] = "offset"
    forged = pure.parse_emission_observation(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()
    )
    assert (forged.status, forged.detail) == (
        pure.Status.INVALID_RELATION,
        "window structural argument roles",
    )


@pytest.mark.parametrize("form", paired_forms.S10)
def test_pure_keeps_refusing_mysql_conditional_counts(tmp_path, form):
    """The pure reader judges a paired S10 document on its own: as before, it
    refuses every MySQL conditional count and test of a group."""
    observed = pure.parse_emission_observation(_pure_document(tmp_path, form))
    assert (observed.status, observed.detail) == (
        pure.Status.INVALID_RELATION,
        "conditional aggregate shape",
    )
