"""Compiled data boundaries stay separate from source and live authority."""

import json
import math
from types import SimpleNamespace

import pytest

from pietto._project import project_compiled_schema as wire
from pietto._project.project_compiled_verification import verify_description
from pietto._project.project_compiled_build import _Export
from pietto.ast_nodes import (
    CastExpr,
    ConditionalExpr,
    LiteralExpr,
    MembershipExpr,
    Nullability,
    Span,
    TypeExpr,
)
from pietto.semantic.expressions import (
    resolved_binary_value_type,
    resolved_literal_value_type,
    resolved_unary_value_type,
)
from pietto.semantic.model import EffectiveNullability, ValueTypeKind
from pietto.semantic.relation_limits import MAX_RELATION_LIMIT, valid_resolved_limit

from pathlib import Path
from typing import Any
from _pietto_sql_query_parameters import (
    MYSQL_TYPED_OPEN,
    MYSQL_TYPED_REFUSED,
    typed_case,
)
from _pietto_sql_emission import LPAD_NOW_PAIRS, LPAD_NOW_REFUSALS, lpad_now_world
from pietto._project.project_sql_emission import serialize_project_sql_emission


def data_only():
    # A decoder fixture, deliberately not a valid executable graph or trusted
    # build. An internally consistent envelope must not confer authority.
    return wire.Description(
        (*wire.VERSIONS, "a" * 64),
        "a" * 64,
        wire.Address("entry", 0),
        tuple((name, ()) for name in wire.MEMBERS),
    )


@pytest.mark.parametrize(
    "tag,value",
    [
        ("Bool", False),
        ("Bool", True),
        ("Int", -(2**63)),
        ("Int", 2**63 - 1),
        ("Float", 0.0),
        ("Float", -0.0),
        ("Float", 1.25),
        ("Text", "雪e\u0301😀 ? %s $1\0"),
        ("Text", ""),
    ],
)
def test_exact_scalar_data(tag, value):
    encoded = wire.scalar_wire(wire.Scalar(tag, value))
    result = wire.scalar_read(encoded)
    assert type(result.value) is type(value)
    if type(value) is float:
        assert type(result.value) is float
        assert result.value.hex() == value.hex()
    else:
        assert result.value == value


@pytest.mark.parametrize(
    "value",
    [
        ["Int", True],
        ["Int", "01"],
        ["Int", "-0"],
        ["Int", str(2**63)],
        ["Bool", 1],
        ["Bool", "true"],
        ["Float", 0.0],
        ["Float", "nan"],
        ["Float", "inf"],
        ["Float", "0x0p+0"],
        ["Text", None],
        ["Text", "\ud800"],
        ["Decimal", "1.00"],
        ["Timestamp", "2000-01-01"],
        ["UUID", "00000000-0000-0000-0000-000000000000"],
    ],
)
def test_bindable_tags_do_not_expand(value):
    with pytest.raises(wire.CompiledError, match="COMPILED_SCALAR"):
        wire.scalar_read(value)


def test_decoder_is_not_an_authority_constructor():
    description = data_only()
    raw = wire.encode(description)
    assert wire.decode(raw) == description
    with pytest.raises(wire.CompiledError, match="COMPILED_QUERY"):
        verify_description(wire.decode(raw))
    assert wire.content_pin(raw) != wire.content_pin(raw + b" ")


@pytest.mark.parametrize(
    "change,category",
    [
        (lambda v: v.update(format="pietto.sql-emission-observation.v1"), "FORMAT"),
        (lambda v: v.update(extra="unrecognized"), "HEADER"),
        (lambda v: v["members"].reverse(), "MEMBERS"),
        (lambda v: v["members"].pop(), "MEMBERS"),
        (lambda v: v["members"].append(v["members"][0]), "MEMBERS"),
        (lambda v: v.update(query=["entry", True]), "ADDRESS"),
    ],
)
def test_closed_envelope_corruption(change, category):
    value = json.loads(wire.encode(data_only()))
    change(value)
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    with pytest.raises(wire.CompiledError, match="COMPILED_" + category):
        wire.decode(raw)


def test_duplicate_trailing_unicode_and_depth_refuse():
    raw = wire.encode(data_only())
    with pytest.raises(wire.CompiledError, match="DUPLICATE_KEY"):
        wire.decode(raw.replace(b'{"format":', b'{"format":"wrong","format":', 1))
    for invalid in (raw + b"{}", b'"\xff"', raw + b"\n"):
        with pytest.raises(wire.CompiledError):
            wire.decode(invalid)
    with pytest.raises(wire.CompiledError, match="DEPTH_LIMIT"):
        wire.decode(b"[" * (wire.MAX_DEPTH + 1) + b"0" + b"]" * (wire.MAX_DEPTH + 1))


def test_original_scalar_rules_are_available_without_source_nodes():
    integer = resolved_literal_value_type(4)
    boolean = resolved_literal_value_type(True)
    floating = resolved_literal_value_type(-0.0)
    text = resolved_literal_value_type("original")
    assert integer.resolved_type.name == "Int"
    assert boolean.resolved_type.name == "Bool"
    assert floating.resolved_type.name == "Float"
    assert text.resolved_type.name == "Text"
    assert integer.nullability is EffectiveNullability.NON_NULL
    result, error = resolved_binary_value_type("+", integer, floating)
    assert result.resolved_type.name == "Float" and error is None
    assert result.nullability is EffectiveNullability.UNKNOWN
    result, error = resolved_binary_value_type("and", boolean, integer)
    assert result.kind is ValueTypeKind.UNKNOWN and error == "Bool operands"
    result, error = resolved_unary_value_type(text)
    assert result.kind is ValueTypeKind.UNKNOWN and error == "numeric operand"
    # Int / Int divides as SQL does: an Int truncated toward zero.
    result, error = resolved_binary_value_type("/", integer, integer)
    assert result.resolved_type.name == "Int" and error is None
    assert result.nullability is EffectiveNullability.UNKNOWN
    assert not math.copysign(1.0, -0.0) > 0


def test_compiled_literal_ancestry_retains_new_expression_parent_kinds():
    span = Span(path="compiled.pietto", line=1, column=1, end_line=1, end_column=2)
    conditional = ConditionalExpr(
        span=span,
        when_true=LiteralExpr(span=span, value=1),
        condition=LiteralExpr(span=span, value=True),
        when_false=LiteralExpr(span=span, value=2),
    )
    membership = MembershipExpr(
        span=span,
        value=LiteralExpr(span=span, value=1),
        options=(LiteralExpr(span=span, value=1),),
        negated=True,
    )
    cast = CastExpr(
        span=span,
        value=LiteralExpr(span=span, value=1),
        target=TypeExpr(
            span=span,
            name="Float",
            arguments=(),
            nullability=Nullability.IMPLICIT,
        ),
    )
    owner = object()
    sites = tuple(
        SimpleNamespace(
            position=SimpleNamespace(
                ancestry=((parent, position),),
                literal=literal,
                owner=owner,
                role=SimpleNamespace(value="select"),
            ),
            disposition=SimpleNamespace(value="bound"),
            reason=None,
        )
        for parent, position, literal in (
            (conditional, 1, conditional.condition),
            (membership, 1, membership.options[0]),
            (cast, 0, cast.value),
        )
    )
    exporter = object.__new__(_Export)
    exporter.request = SimpleNamespace(
        plan=SimpleNamespace(literal_sites=sites, literal_slots=(), parameters=())
    )
    exporter.artifact = SimpleNamespace(parameter_uses=())
    exporter.sites = {}
    exporter.literals = {}
    exporter.slots = {}
    records = []

    def declaration(owner):
        return owner

    def add(kind, *values):
        records.append((kind, *values))
        return wire.Address(kind, len(records) - 1)

    exporter.declaration = declaration
    exporter.add = add

    exporter.literal_records()

    assert [record[4] for record in records if record[0] == "site"] == [
        (("conditional", 1),),
        (("membership", 1),),
        (("cast", 0),),
    ]


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, True),
        (MAX_RELATION_LIMIT, True),
        (MAX_RELATION_LIMIT + 1, False),
        (-1, False),
        (True, False),
        (1.0, False),
        ("1", False),
    ],
)
def test_static_limit_rule_does_not_coerce(value, expected):
    assert valid_resolved_limit(value) is expected


def _header(record, field, value):
    values = list(record.values)
    values[wire.FIELDS["parameter"].index(field)] = value
    return type(record)(record.address, tuple(values))


def _parameterized(directory, target, variant, case="Q_query_parameters"):
    """The compiled root of a published conformance query (by default the v2
    query that declares parameters)."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled

    item = probe.fixture(target, case, variant)
    _, outcome = probe.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    return build_compiled(outcome.artifact)


def _relabelled(payload, marker):
    """The same canonical payload under another format marker."""
    document = json.loads(payload)
    return json.dumps(
        {**document, "format": marker}, ensure_ascii=False, separators=(",", ":")
    ).encode()


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_parameterized_root_travels_as_a_v2_payload(tmp_path, target):
    from pietto._project.model import CompiledProjectInput
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    built = _parameterized(tmp_path / "v2", target, "bind")
    assert json.loads(built.payload)["format"] == wire.PARAMETERIZED_FORMAT
    assert wire.PARAMETERIZED_FORMAT != wire.FORMAT
    assert built.compatibility[: len(wire.VERSIONS)] == wire.VERSIONS
    # The unbound template decodes byte for byte and loads under its records.
    assert wire.encode(wire.decode(built.payload)) == built.payload
    loaded = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert [(p.name, p.tag, p.nullable) for p in loaded.parameters] == [
        ("low", "Int", False),
        ("label", "Text", True),
    ]
    # The marker names the records: a v1 marker on it, a v2 marker on a root
    # without parameters and an unknown marker are all refused.
    plain = _parameterized(tmp_path / "v1", target, "bag", "G_emission_table_bag")
    assert json.loads(plain.payload)["format"] == wire.FORMAT
    for payload, marker, word in (
        (built.payload, wire.FORMAT, "COMPILED_CANONICAL"),
        (plain.payload, wire.PARAMETERIZED_FORMAT, "COMPILED_CANONICAL"),
        (built.payload, "pietto.compiled-execution.v3", "COMPILED_FORMAT"),
    ):
        with pytest.raises(wire.CompiledError, match=f"^{word}$"):
            wire.decode(_relabelled(payload, marker))
    description = built.root.description
    header = [r for r in description.records if r.address.kind == "parameter"]
    assert [(r.get("label"), r.get("tag")) for r in header] == [
        ("low", "Int"),
        ("label", "Text"),
    ]

    def forged(change):
        return type(description)(
            description.compatibility,
            description.producer,
            description.query,
            tuple(
                (name, tuple(change(r) for r in records))
                for name, records in description.members
            ),
        )

    reordered = forged(lambda r: _header(r, "ordinal", 0) if r is header[1] else r)
    # One caller entry must never bind two parameters.
    renamed = forged(lambda r: _header(r, "label", "low") if r is header[1] else r)
    unnamed = forged(lambda r: _header(r, "label", "a b;--") if r is header[1] else r)
    for damaged in (reordered, renamed, unnamed):
        with pytest.raises(wire.CompiledError, match="^COMPILED_PARAMETER$"):
            verify_description(damaged)

    def declared(count):
        # Well-formed header records after the two the query declares.
        extra = tuple(
            type(header[0])(
                wire.Address("parameter", i),
                _header(_header(header[0], "ordinal", i), "label", "p%d" % i).values,
            )
            for i in range(len(header), count)
        )
        return type(description)(
            description.compatibility,
            description.producer,
            description.query,
            tuple(
                (name, records + extra if name == "parameters" else records)
                for name, records in description.members
            ),
        )

    verify_description(declared(64))
    with pytest.raises(wire.CompiledError, match="^COMPILED_PARAMETER$"):
        verify_description(declared(65))
    retyped = forged(lambda r: _header(r, "tag", "Text") if r is header[0] else r)
    root = CompiledProjectInput(
        retyped,
        wire.content_pin(wire.encode(retyped)),
        retyped.producer,
        retyped.compatibility,
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_OPERATOR_TYPE$"):
        prepare_compiled_template(root)


WINDOW_COUNTS = """query result(k: Int, b: Int):
    from rows
    select:
        id
        a = lag(id, k) window(order by id)
        n = ntile(b) window(order by id)
"""


def _forged(description, change):
    return type(description)(
        description.compatibility,
        description.producer,
        description.query,
        tuple(
            (name, tuple(change(r) for r in records))
            for name, records in description.members
        ),
    )


def test_a_window_parameter_argument_is_tied_to_its_own_read(tmp_path, monkeypatch):
    """Export, structure and semantics each re-derive a window count read: a
    swapped read, a nullable count and a widened interval are all refused."""
    from dataclasses import replace
    import _pietto_sql_emission as probe
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_verification import verify_export
    from pietto._project.project_completed_semantics import (
        derive_compiled_semantics,
        verify_compiled_semantics,
    )

    item = probe.parameterized_fixture("postgres", WINDOW_COUNTS)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    built = build_compiled(outcome.artifact)
    description = built.root.description
    values = [r for r in description.records if r.address.kind == "window_value"]
    (value, offset), (bucket,) = (v.get("arguments") for v in values)
    assert (offset[0], bucket[0]) == ("offset", "bucket")
    assert offset[1].kind == bucket[1].kind == "parameter_read"
    position = wire.FIELDS["window_value"].index("arguments")

    def arguments(record, replaced):
        changed = list(record.values)
        changed[position] = replaced
        return type(record)(record.address, tuple(changed))

    def one_sided(record):
        if record is not values[0]:
            return record
        return arguments(record, (value, ("offset", bucket[1])))

    def swapped(record):
        if record is values[1]:
            return arguments(record, (("bucket", offset[1]),))
        return one_sided(record)

    # A valid-looking read of the other count parameter: the two reads trade
    # places, so each keeps one reader and only the export sees the swap.
    with pytest.raises(wire.CompiledError, match="^COMPILED_EXPORT_WINDOW_PARAMETER$"):
        verify_export(_forged(description, swapped), outcome.artifact)
    # A one-sided swap leaves a header read outside every expression.
    with pytest.raises(wire.CompiledError, match="^COMPILED_PARAMETER_OWNER$"):
        verify_description(_forged(description, one_sided))
    header = [r for r in description.records if r.address.kind == "parameter"]
    nullable = _forged(
        description, lambda r: _header(r, "nullable", True) if r is header[0] else r
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_WINDOW_PARAMETER$"):
        verify_description(nullable)
    root = built.root
    verify_compiled_semantics(derive_compiled_semantics(root, (), (1, 1)))
    with pytest.raises(wire.CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
        derive_compiled_semantics(root, (), (0, 0))
    exact = windowing.count_realization

    def widened(*arguments, **keywords):
        found = exact(*arguments, **keywords)
        if keywords.get("bound") or found is None:
            return found
        return replace(
            found,
            domain={**found.domain, "min": "0"},
            proven_int_range=(0, (1 << 31) - 1),
        )

    # The template's bucket interval claims 0: only the verifier refuses it.
    with monkeypatch.context() as patch:
        patch.setattr(windowing, "count_realization", widened)
        forged = derive_compiled_semantics(root, (), None)
    with pytest.raises(wire.CompiledError, match="^COMPILED_SEMANTIC_REALIZATION$"):
        verify_compiled_semantics(forged)


def test_a_parameter_read_fact_keeps_its_proven_int_range(tmp_path, monkeypatch):
    from dataclasses import replace
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_completed_semantics import (
        derive_compiled_semantics,
        verify_compiled_semantics,
    )

    root = _parameterized(tmp_path, "postgres", "preserve").root
    verify_compiled_semantics(derive_compiled_semantics(root, (), (1, "x")))
    # `above = low + 1` leaves the Int carrier for the largest value.
    with pytest.raises(wire.CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
        derive_compiled_semantics(root, (), (2**63 - 1, "x"))
    exact = physical.parameter_realization

    def narrowed(*arguments, **keywords):
        found = exact(*arguments, **keywords)
        return replace(found, proven_int_range=(0, 0)) if found.tag == "Int" else found

    # A derivation whose Int read claims a narrower proof than its value
    # passes its own arithmetic check, so only the verifier can refuse it.
    with monkeypatch.context() as patch:
        patch.setattr(physical, "parameter_realization", narrowed)
        forged = derive_compiled_semantics(root, (), (2**63 - 1, "x"))
    with pytest.raises(wire.CompiledError, match="^COMPILED_SEMANTIC_REALIZATION$"):
        verify_compiled_semantics(forged)


def _set(record, field, value):
    values = list(record.values)
    values[wire.FIELDS[record.address.kind].index(field)] = value
    return type(record)(record.address, tuple(values))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_repinned_v2_payload_with_valid_looking_swaps_never_loads(tmp_path, target):
    """Each forgery keeps every value well formed and is re-pinned, so only
    the loader's own derivation can refuse it."""
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    built = _parameterized(tmp_path, target, "bind")
    description = built.root.description
    low, label = (r for r in description.records if r.address.kind == "parameter")
    first_read = next(
        r for r in description.records if r.address.kind == "parameter_read"
    )
    first, second = [r for r in description.records if r.address.kind == "native_use"][
        :2
    ]
    forgeries = {
        # label NULL becomes illegal, which its own port type still reads.
        "not_null_label": (lambda r: _set(r, "nullable", False) if r is label else r),
        "float_low": (lambda r: _set(r, "tag", "Float") if r is low else r),
        "read_of_label": (
            lambda r: _set(r, "parameter", label.address) if r is first_read else r
        ),
        "server_index": (
            lambda r: _set(r, "index", r.get("index") + 1) if r is first else r
        ),
        "swapped_occurrences": (
            lambda r: (
                _set(r, "slot", second.get("slot"))
                if r is first
                else _set(r, "slot", first.get("slot"))
                if r is second
                else r
            )
        ),
        "swapped_ordinals": (
            lambda r: (
                _set(r, "ordinal", 1)
                if r is low
                else _set(r, "ordinal", 0)
                if r is label
                else r
            )
        ),
    }
    words = {
        "not_null_label": "COMPILED_PORT_TYPE",
        "float_low": "COMPILED_PHYSICAL_DOMAIN",
        "read_of_label": "COMPILED_OPERATOR_TYPE",
        "server_index": "COMPILED_PLAN_USES",
        "swapped_occurrences": "COMPILED_PLAN_USES"
        if target == "postgres"
        else "COMPILED_EMISSION_PARAMETER_INVENTORY",
        "swapped_ordinals": "COMPILED_PARAMETER",
    }
    for name, change in forgeries.items():
        forged = wire.Description(
            description.compatibility,
            description.producer,
            description.query,
            tuple(
                (member, tuple(change(r) for r in records))
                for member, records in description.members
            ),
        )
        raw = wire.encode(forged)
        assert json.loads(raw)["format"] == wire.PARAMETERIZED_FORMAT
        with pytest.raises(wire.CompiledError) as refused:
            prepare_compiled_template(
                load_compiled(
                    raw,
                    expected_pin=wire.content_pin(raw),
                    accepted_producer=forged.producer,
                    accepted_compatibility=forged.compatibility,
                )
            )
        assert (name, str(refused.value)) == (name, words[name])
        # The caller's own pin names the original bytes only.
        with pytest.raises(wire.CompiledError, match="^COMPILED_CONTENT_PIN$"):
            load_compiled(
                raw,
                expected_pin=built.pin,
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )


STAGED_BODIES = {
    "having": (
        "query result:\n    from rows\n    let a = id\n    where id > 2\n"
        "    group by:\n        id\n    select:\n        k = id\n"
        "        n = count()\n    having:\n        n > 1\n",
        ["let", "where", "satisfying", "projection"],
    ),
    "qualify": (
        "query result:\n    from rows\n    select:\n        id\n"
        "        r = row_number() window(order by id)\n"
        "    qualify row_number() window(order by id) <= 2\n",
        ["qualify", "projection"],
    ),
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("name", STAGED_BODIES)
def test_a_repinned_row_never_loads_under_another_stage(tmp_path, target, name):
    """A row's stage is its body's: only a let adds a value to what it
    carries, only an aggregate or a window feeds a having or a qualify, and
    only the projection ends the chain. Each other label, its predicate
    dropped or added to match, is re-pinned and never loads; a WHERE
    relabelled a let would replay a pass-through CTE."""
    import pietto.execution as execution
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    body, expected = STAGED_BODIES[name]
    _, outcome = parameterized_case(tmp_path, target, body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    description = built.root.description
    rows = [r for r in description.records if r.address.kind == "row"]
    assert [r.get("stage") for r in rows] == expected
    filters = ("where", "satisfying", "qualify")
    for row in rows:
        for stage in ("let", *filters, "projection"):
            if stage == row.get("stage"):
                continue
            predicate = (
                (row.get("predicate") or row.get("values")[-1])
                if stage in filters
                else None
            )

            def relabel(r, row=row, stage=stage, predicate=predicate):
                if r is not row:
                    return r
                return _set(_set(r, "predicate", predicate), "stage", stage)

            raw = wire.encode(_forged(description, relabel))
            with pytest.raises(wire.CompiledError) as refused:
                load_compiled(
                    raw,
                    expected_pin=wire.content_pin(raw),
                    accepted_producer=built.producer,
                    accepted_compatibility=built.compatibility,
                )
            assert (row.get("stage"), stage, str(refused.value)) == (
                row.get("stage"),
                stage,
                "COMPILED_ROW_SHAPE",
            )
            if (row.get("stage"), stage) == ("where", "let"):
                with pytest.raises(execution.RequestRejected) as rejected:
                    execution.load_bundle(
                        raw,
                        expected_pin=wire.content_pin(raw),
                        accepted_producer=built.producer,
                        accepted_compatibility=built.compatibility[-1],
                    )
                assert rejected.value.detail == "COMPILED_ROW_SHAPE"


OPERAND_GRAPH = """table result:
    from rows
    where lower(text) != "x" and (%s)
    group by text
    select:
        text
        n = count(lower(text))
""" % " or ".join(['text == "a"'] * 18)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_repinned_operand_cycle_or_dag_is_refused_before_any_walk(tmp_path, target):
    """The operand graph is proven acyclic and its tree expansion bounded
    before any check walks it: a re-pinned cycle or doubling DAG in a row
    predicate or an aggregate argument is refused at once, not after
    exhausting time, memory or the stack."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled

    item = probe.parameterized_fixture(target, OPERAND_GRAPH)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    built = build_compiled(outcome.artifact)
    description = built.root.description
    operations = [r for r in description.records if r.address.kind == "operation"]
    (counted,) = (
        a
        for r in description.records
        if r.address.kind == "aggregate_value"
        for a in r.get("arguments")
    )
    (row,) = (
        r
        for r in operations
        if r.get("operator")[1] == "lower" and r.address != counted
    )
    chain = {
        r.address
        for r in operations
        if r.get("operator")[1] == "or" and r.get("operands")[0].kind == "operation"
    }
    (where,) = (
        r
        for r in description.records
        if r.address.kind == "row" and r.get("predicate") is not None
    )
    forgeries = {
        # Each `or` reads its left operand twice: 17 operations unfold to
        # 2**17 comparisons.
        "row_dag": lambda r: (
            _set(r, "operands", (r.get("operands")[0],) * 2)
            if r.address in chain
            else r
        ),
        "aggregate_cycle": lambda r: (
            _set(r, "operands", (counted,)) if r.address == counted else r
        ),
        "not_an_address": lambda r: (
            _set(r, "operands", (0,)) if r.address == counted else r
        ),
        "row_cycle": lambda r: _set(r, "operands", (row.address,)) if r is row else r,
        # A row value that names a port is no expression root.
        "root_not_value": lambda r: (
            _set(r, "values", (r.get("outputs")[0], *r.get("values")[1:]))
            if r is where
            else r
        ),
        # The predicate unfolds to fewer than a hundred records; read 2048
        # times as row values, it is bounded by every reference, not once.
        "shared_roots": lambda r: (
            _set(r, "values", (r.get("predicate"),) * 2048) if r is where else r
        ),
    }
    refused = {}
    for name, change in forgeries.items():
        raw = wire.encode(_forged(description, change))
        with pytest.raises(wire.CompiledError) as caught:
            load_compiled(
                raw,
                expected_pin=wire.content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )
        refused[name] = str(caught.value)
    assert refused == {
        "row_dag": "COMPILED_EXPRESSION_EXPANSION",
        "aggregate_cycle": "COMPILED_EXPRESSION_CYCLE",
        "not_an_address": "COMPILED_REFERENCE",
        "row_cycle": "COMPILED_EXPRESSION_CYCLE",
        "root_not_value": "COMPILED_REFERENCE",
        "shared_roots": "COMPILED_EXPRESSION_EXPANSION",
    }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_only_the_entry_query_and_its_lets_read_the_header(tmp_path, target):
    """A let's read travels in the v2 root and binds; a re-pinned root that
    moves a read into another declaration is not one compile_query makes."""
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
    )

    built = _parameterized(tmp_path / "let", target, "let_bind")
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    literals = tuple(
        (s, s.original.site.position.literal.value) for s in template.slots
    )
    bound = bind_values(
        template, literals, tuple(zip(template.parameters, (4, "x"), strict=True))
    )
    assert bound.artifact.rendered.sql == template.artifact.rendered.sql
    assert bound.arguments == (
        (4, 3, "x", 1) if target == "postgres" else (4, 3, "x", 4, 1, 4)
    )

    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled

    item = probe.fixture(target, "Q_query_parameters", "preserve")
    source = (
        item["source"]
        .replace(
            "query result(",
            "table t:\n    from rows\n    where plain > 5\n    select:\n        id\n"
            "        plain\nquery result(",
        )
        .replace("    from rows\n    where id > low", "    from t\n    where id > low")
    )
    _, outcome = probe.build_case(
        tmp_path / "two", source, item["contract"], item["policy"]
    )
    description = build_compiled(outcome.artifact).root.description
    records = {r.address: r for r in description.records}
    (table,) = (
        r
        for r in description.records
        if r.address.kind == "declaration" and r.get("label") == "t"
    )
    (outer,) = (
        r
        for r in description.records
        if r.address.kind == "operation"
        and r.get("operator") == ("comparison", ">")
        and any(o.kind == "parameter_read" for o in r.get("operands"))
    )
    (inner,) = (
        r
        for r in description.records
        if r.address.kind == "operation"
        and r.get("operator") == ("comparison", ">")
        and any(
            records[u].get("owner") == table.address
            for u in records
            if u.kind == "row" and records[u].get("predicate") == r.address
        )
    )
    # Swap the leaves: `t` now reads `low`, the entry reads the literal.
    read = next(o for o in outer.get("operands") if o.kind == "parameter_read")
    leaf = inner.get("operands")[1]

    def change(record):
        if record is outer:
            return _set(record, "operands", (outer.get("operands")[0], leaf))
        if record is inner:
            return _set(record, "operands", (inner.get("operands")[0], read))
        return record

    swapped = wire.Description(
        description.compatibility,
        description.producer,
        description.query,
        tuple(
            (member, tuple(change(r) for r in records_))
            for member, records_ in description.members
        ),
    )

    # `t` aggregates the entry's `low + 1`. Records of two kinds may come in
    # either order, so moving the aggregate last lets the entry's row walk
    # the shared operation first; `t` must still be refused.
    _, outcome = probe.build_case(
        tmp_path / "order",
        item["source"].split("query result(", 1)[0]
        + "table t:\n    from rows\n    group by plain\n    select:\n        plain\n"
        "        n = max(id)\nquery result(low: Int):\n    from t\n"
        "    where n > low + 1\n    select:\n        plain\n",
        item["contract"],
        item["policy"],
    )
    ordered = build_compiled(outcome.artifact).root.description
    (shared,) = (
        r
        for r in ordered.records
        if r.address.kind == "operation"
        and any(o.kind == "parameter_read" for o in r.get("operands"))
    )
    (value,) = (r for r in ordered.records if r.address.kind == "aggregate_value")
    (aggregate,) = (r for r in ordered.records if r.address.kind == "aggregate")
    moved = wire.Description(
        ordered.compatibility,
        ordered.producer,
        ordered.query,
        tuple(
            (
                member,
                tuple(
                    _set(r, "arguments", (shared.address,)) if r is value else r
                    for r in records_
                    if r is not aggregate
                )
                + ((aggregate,) if member == "structure" else ()),
            )
            for member, records_ in ordered.members
        ),
    )
    for forged in (swapped, moved):
        raw = wire.encode(forged)
        with pytest.raises(wire.CompiledError, match="^COMPILED_PARAMETER_OWNER$"):
            load_compiled(
                raw,
                expected_pin=wire.content_pin(raw),
                accepted_producer=forged.producer,
                accepted_compatibility=forged.compatibility,
            )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_let_read_only_by_relation_reads_binds_its_header_reads(tmp_path, target):
    """Lets read only by `exists`, `scalar` and `in` travel in the v2 root,
    and a binding sends their reads in the template's placeholder order."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
    )

    body = (
        "query result(low: Int, high: Int):\n"
        "    let a:\n        from rows\n        where id > low\n"
        "        select:\n            id\n"
        "    let b:\n        from rows\n        where exists a and id < high + low\n"
        "        select:\n            n = count()\n"
        "    from rows\n"
        "    where id >= high and id in a and id <= scalar b.n and not exists a\n"
        "    select:\n        record_id = id\n"
    )
    _, outcome = parameterized_case(tmp_path, target, body)
    built = build_compiled(outcome.artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert [p.name for p in template.parameters] == ["low", "high"]
    bound = bind_values(
        template, (), tuple(zip(template.parameters, (1, 5), strict=True))
    )
    assert bound.artifact.rendered.sql == template.artifact.rendered.sql
    assert bound.arguments == ((1, 5) if target == "postgres" else (1, 5, 1, 5))
    # `high + low` in let b waits for the binding.
    with pytest.raises(ValueError, match="^BINDING_INVALID$"):
        bind_values(
            template,
            (),
            tuple(zip(template.parameters, (1, 2**63 - 1), strict=True)),
        )


def test_a_stddev_template_binds_its_header_read_and_renders_the_same_sql(tmp_path):
    """Lane F: a loaded compiled and a live PostgreSQL template of Int and
    Float `stddev` under a WHERE header parameter bind it and render the
    emitted SQL byte for byte."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    select:\n        spread = stddev(id)\n"
        "        ratio_spread = stddev(ratio)\n"
    )
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == template.artifact.rendered.sql
        assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
        assert bound.artifact.rendered.sql.count(b"SQRT(CAST(VAR_SAMP(") == 2
        assert bound.arguments == (3,)


def test_a_variance_template_binds_its_header_read_and_renders_the_same_sql(
    tmp_path,
):
    """A loaded compiled and a live PostgreSQL template of Int and Float
    `variance`, `pvariance` and `pstdev` under GROUP BY and a WHERE header
    parameter bind it and render the emitted SQL byte for byte."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    group by flag\n    select:\n        flag\n"
        "        v = variance(id)\n        pv = pvariance(id)\n"
        "        ps = pstdev(id)\n        ratio_v = variance(ratio)\n"
        "        ratio_pv = pvariance(ratio)\n        ratio_ps = pstdev(ratio)\n"
    )
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        sql = bound.artifact.rendered.sql
        assert sql == template.artifact.rendered.sql
        assert sql == outcome.artifact.rendered.sql
        assert sql.count(b"CAST(VAR_SAMP(") == 2
        assert b"SQRT(CAST(VAR_SAMP(" not in sql
        assert sql.count(b"CAST(VAR_POP(") == 4
        assert sql.count(b"SQRT(CAST(VAR_POP(") == 2
        assert bound.arguments == (3,)


@pytest.mark.parametrize(
    "body",
    (
        "    from rows\n    where id > low\n    select:\n        id\n"
        "        total = sum(id) window(partition by flag order by id)\n"
        "        n = count() window(partition by flag)\n"
        "        mean = avg(id) window(order by id rows between 1 preceding"
        " and current row)\n"
        "        low_id = min(id) window(order by id)\n"
        "        high_id = max(id) window(order by id)\n",
        "    from rows\n    where id > low\n    group by:\n        flag\n"
        "    select:\n        flag\n        total = sum(id)\n"
        "        running = sum(total) window(order by flag)\n",
        "    from rows\n    where id > low\n    select:\n        id\n"
        "    qualify:\n        count(id) window(partition by flag) > 1\n",
        "    from rows\n    let other = rows\n"
        "    inner join other on rows.id == other.id\n    where rows.id > low\n"
        "    select:\n        id = rows.id\n"
        "        total = sum(other.id) window(partition by rows.flag order by rows.id)\n",
    ),
    ids=("selected", "grouped", "qualify", "joined"),
)
def test_an_aggregate_window_template_binds_and_renders_the_emitted_sql(tmp_path, body):
    """A PostgreSQL project's aggregate windows, selected, over grouped rows,
    in a hidden QUALIFY window and over JOIN rows, under a WHERE header
    parameter, bind through a loaded compiled bundle and a live template and
    render the emitted SQL byte for byte."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    _, outcome = parameterized_case(
        tmp_path, "postgres", "query result(low: Int):\n" + body
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
        assert b") OVER (" in bound.artifact.rendered.sql
        assert bound.arguments == (3,)


def test_windows_over_computed_let_keys_bind_and_render_the_emitted_sql(tmp_path):
    """Windows whose PARTITION BY and ORDER BY keys name computed `let`s (a
    comparison, a `def` call), selected, named and in QUALIFY, under a WHERE
    header read, bind through a live template and a loaded compiled bundle and
    render the emitted PostgreSQL byte for byte."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "def far(v: Int) -> Bool:\n    return v > 1\n\n"
        "query result(low: Int):\n    from rows\n    let off = id != 1\n"
        "    let f = far(id)\n"
        "    let ordered = window(partition by off order by f desc)\n"
        "    where id >= low\n    select:\n        record_id = id\n"
        "        n = row_number() window(partition by off order by f desc, id)\n"
        "        r = rank() window ordered\n"
        "    qualify row_number() window(partition by off order by id) <= 2\n"
    )
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (0,), strict=True))
        )
        assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
        assert bound.arguments == (0,)
        sql = bound.artifact.rendered.sql
        # Each computed key is a stage column the windows read by name.
        assert b'"order.id" <> CAST(1 AS pg_catalog.int8))' in sql
        assert b' > CAST(1 AS pg_catalog.int8)) AS "c' in sql
        assert sql.count(b"ROW_NUMBER() OVER (PARTITION BY ") == 2
        assert b'RANK() OVER "w0"' in sql


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_half_open_range_template_renders_the_emitted_sql(tmp_path, target):
    """The recommended half-open range `start <= ts < stop` in a query, over
    Timestamp and Date with distinct start and stop fields, binds through a
    loaded compiled bundle and a live template and renders the emitted SQL
    byte for byte, start before the value and the value before stop."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    checked, outcome = probe.temporal_case(
        tmp_path,
        target,
        "    from rows\n    where ts2 <= ts < ts3 and d2 <= d < d3\n"
        "    select:\n        t = ts\n",
        fields=(
            *probe.TEMPORAL_FIELDS,
            ("ts3", "Timestamp", True),
            ("d3", "Date", True),
        ),
        entry="query result:",
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    q = '"' if target == "postgres" else "`"
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(template, ())
        assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
        for start, value, stop in (("ts2", "ts", "ts3"), ("d2", "d", "d3")):
            assert (
                f"(({q}s0{q}.{q}{start}{q} <= {q}s0{q}.{q}{value}{q}) AND "
                f"({q}s0{q}.{q}{value}{q} < {q}s0{q}.{q}{stop}{q}))"
            ).encode() in bound.artifact.rendered.sql


# The two-level route: `per_lhs` counts the rhs rows of each lhs row, grouped
# by the declared key of lhs, and `result` sums its rows, one per lhs row.
TWO_LEVEL_ROUTE = """shape Row:
    id: Int
    key: Int | None
    row_key = unique(id)
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
query per_lhs:
    from lhs
    let r = rhs
    left join r on r.key == lhs.id
    group by:
        lhs.id
        lhs.key
    select:
        id = lhs.id
        key = lhs.key
        n = count(r.id)
query result(low: Int):
    from per_lhs
    where id > low
    group by key
    select:
        key
        ids = sum(id)
        n = sum(n)
"""


def test_the_two_level_route_template_renders_the_emitted_sql(tmp_path):
    """The two-level route on PostgreSQL, under a header parameter of the
    second query, binds through a loaded compiled bundle and a live template
    and renders the emitted SQL byte for byte: one COUNT per lhs key, then
    the two checked SUMs over its rows."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    item = probe.join_witness(
        "postgres", {"main.pietto": TWO_LEVEL_ROUTE}, policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    assert json.loads(built.payload)["format"] == wire.PARAMETERIZED_FORMAT
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    sql = outcome.artifact.rendered.sql
    for template in (compiled, prepare_live_template(outcome.artifact)):
        assert [(p.name, p.nullable) for p in template.parameters] == [("low", False)]
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (7,), strict=True))
        )
        assert bound.artifact.rendered.sql == sql
        assert bound.arguments == (7,)
    assert sql.count(b"COUNT(") == 1 and sql.count(b" LEFT JOIN ") == 1
    assert sql.count(b"CAST(SUM(CAST(") == 2 and sql.count(b" GROUP BY ") == 2


def test_lpad_and_add_months_templates_render_the_emitted_sql(tmp_path):
    """Project PostgreSQL `lpad` under a WHERE header parameter, MySQL `lpad`
    in its cell and PostgreSQL `add_months` over Date fields bind through a
    loaded compiled bundle and a live template and render the emitted SQL
    byte for byte; the MySQL cell holds no server parameter."""
    import _pietto_sql_emission as probe
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    _, padded = parameterized_case(
        tmp_path / "pad",
        "postgres",
        "query result(low: Int):\n    from rows\n    where id > low\n"
        '    select:\n        padded = lpad(text, 5, "0")\n',
    )
    _, dated = probe.temporal_case(
        tmp_path / "date",
        "postgres",
        "    from rows\n    select:\n        later = add_months(d, 1)\n"
        "        moved = add_months(d2, id)\n",
        entry="query result:",
    )
    _, mysql_padded = parameterized_case(
        tmp_path / "pad",
        "mysql",
        'table result:\n    from rows\n    select:\n        padded = lpad(text, 5, "0")\n',
    )
    for outcome, values, form in (
        (padded, (3,), b"(CASE WHEN length("),
        (mysql_padded, (), b"CASE WHEN CHAR_LENGTH("),
        (dated, (), b" + make_interval(months => CAST("),
    ):
        assert outcome.status == "VERIFIED", outcome.blockers
        assert outcome.artifact is not None
        built = build_compiled(outcome.artifact)
        compiled = prepare_compiled_template(
            load_compiled(
                built.payload,
                expected_pin=built.pin,
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )
        )
        for template in (compiled, prepare_live_template(outcome.artifact)):
            bound = bind_values(
                template, (), tuple(zip(template.parameters, values, strict=True))
            )
            assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
            assert form in bound.artifact.rendered.sql
            assert bound.arguments == values


@pytest.mark.parametrize(
    "target,body,calls",
    (
        (
            "postgres",
            "        hi = max(ratio)\n        s = sum(ratio)\n"
            "        a = avg(ratio)\n        w = sum(id * 2)\n"
            "        l = count_distinct(lower(text))\n",
            (b"COUNT(DISTINCT lower(", b"SUM(CAST((", b"AVG(", b"MIN(", b"MAX("),
        ),
        (
            "mysql",
            "        hi = max(ratio)\n        r = count(ratio)\n"
            "        l = count_distinct(lower(text))\n",
            (b"COUNT(DISTINCT LOWER(", b"COUNT(DISTINCT `", b"MIN(", b"MAX("),
        ),
    ),
)
def test_an_aggregate_parity_template_binds_and_renders_the_same_sql(
    tmp_path, target, body, calls
):
    """S16: Text, Bool, Decimal and Float aggregates and aggregates over row
    expressions (and on PostgreSQL a Float sum and average and an Int
    expression sum), under a WHERE header parameter, bind through a loaded
    compiled bundle and a live template and render byte-equal SQL."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    select:\n        n = count(text)\n"
        "        d = count_distinct(flag)\n        lo = min(money)\n" + body
    )
    _, outcome = parameterized_case(tmp_path, target, body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    sql = outcome.artifact.rendered.sql
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == sql
        assert bound.arguments == (3,)
    for call in calls:
        assert call in sql


def test_a_conditional_count_and_sum_template_binds_its_header_read(tmp_path):
    """The conditional count and sum of a group under a WHERE header
    parameter bind through a loaded compiled bundle and a live PostgreSQL
    template and render byte-equal SQL."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    group by flag\n    select:\n        flag\n"
        "        n = sum(1 for o in group if o.id > 2)\n"
        '        s = sum(o.id for o in group if o.text == "a")\n'
    )
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    sql = outcome.artifact.rendered.sql
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == sql
        assert bound.arguments == (3,)
    assert b"COUNT(CASE WHEN (" in sql
    assert b"COALESCE(CAST(SUM(CASE WHEN (" in sql


def test_a_group_test_template_binds_its_header_read(tmp_path):
    """A loaded compiled and a live PostgreSQL template of `all` and `any` of a
    group under a WHERE header parameter bind it and render the emitted SQL
    byte for byte."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    group by flag\n    select:\n        flag\n"
        "        a = all(o.id > 2 for o in group)\n"
        '        b = any(o.text == "a" for o in group)\n'
    )
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == template.artifact.rendered.sql
        assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
        sql = bound.artifact.rendered.sql
        assert b" THEN NULL ELSE 1 END) = 0)" in sql
        assert b" THEN 1 END) > 0)" in sql
        assert bound.arguments == (3,)


def test_a_median_and_quantile_template_binds_its_header_read(tmp_path):
    """`median` and `quantile` under GROUP BY and a WHERE header parameter
    bind through a loaded compiled bundle and a live PostgreSQL template and
    render byte-equal SQL."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    group by flag\n    select:\n        flag\n"
        "        middle = median(id)\n        high = quantile(id, 0.25)\n"
    )
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    sql = outcome.artifact.rendered.sql
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == sql
        assert bound.arguments == (3,)
    assert sql.count(b"PERCENTILE_CONT(") == 2
    assert b"CAST('0.25' AS pg_catalog.float8)" in sql


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_an_imported_def_renders_the_sql_of_the_same_local_def(tmp_path, target):
    """A query that calls a def another module exports emits the bytes
    of the same def declared locally, and binds through a loaded compiled
    bundle and a live template to them; the importer's alias of a signature
    type name does not apply (the declaring module's alias does)."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    declared = "type Money = Int\ndef pos(x: Money) -> Bool:\n    return x > 0\n"
    body = "    from rows\n    where {}(id)\n    select:\n        t = ts\n"
    _, local = probe.temporal_case(
        tmp_path / "local", target, body.format("pos"), entry=declared + "query result:"
    )
    checked, imported = probe.temporal_case(
        tmp_path / "imported",
        target,
        body.format("p"),
        entry='from "a.pietto" import def pos as p\ntype Money = Text\nquery result:',
        modules={"a.pietto": "export def pos\n" + declared},
    )
    assert checked.verified and imported.status == local.status == "VERIFIED"
    assert imported.artifact is not None and local.artifact is not None
    sql = imported.artifact.rendered.sql
    assert sql == local.artifact.rendered.sql
    built = build_compiled(imported.artifact)
    for template in (
        prepare_live_template(imported.artifact),
        prepare_compiled_template(
            load_compiled(
                built.payload,
                expected_pin=built.pin,
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )
        ),
    ):
        assert bind_values(template, ()).artifact.rendered.sql == sql


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_an_imported_relationship_renders_the_sql_of_the_same_local_one(
    tmp_path, target
):
    """A relationship another module exports, called by the name an
    `as` import binds in ON, a WHERE `any(...)` and SELECT, emits the bytes
    of the same relationship declared locally, its parameter shape the
    declaring module's (which the sources import), and binds through a
    loaded compiled bundle and a live template to them."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    item = probe.join_witness(target, "")
    shape = "shape Row:\n    id: Int\n    key: Int | None\n"
    declared = "relationship Same(left: Row, right: Row):\n    left.id == right.id\n"
    body = (
        f'source lhs: Row = {target}.table("lhs")\n'
        f'source rhs: Row = {target}.table("rhs")\n'
        "query result:\n"
        "    from lhs\n"
        "    inner join rhs on {0}(lhs, rhs)\n"
        "    where any({0}(lhs, other) for other in rhs)\n"
        "    select:\n"
        "        id = lhs.id\n"
        "        flag = {0}(lhs, rhs)\n"
    )
    outcomes = []
    for name, files in (
        ("local", {"main.pietto": shape + declared + body.format("Same")}),
        (
            "imported",
            {
                "a.pietto": "export shape Row, relationship Same\n" + shape + declared,
                "main.pietto": 'from "a.pietto" import shape Row, relationship Same as s\n'
                + body.format("s"),
            },
        ),
    ):
        _, outcome = probe.build_case(
            tmp_path / name, files, item["contract"], item["policy"]
        )
        assert outcome.status == "VERIFIED", outcome.blockers
        assert outcome.artifact is not None
        outcomes.append(outcome.artifact)
    local, imported = outcomes
    sql = imported.rendered.sql
    assert sql == local.rendered.sql
    built = build_compiled(imported)
    for template in (
        prepare_live_template(imported),
        prepare_compiled_template(
            load_compiled(
                built.payload,
                expected_pin=built.pin,
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )
        ),
    ):
        assert bind_values(template, ()).artifact.rendered.sql == sql


def test_a_count_distinct_tuple_template_binds_its_header_read(tmp_path):
    """A loaded compiled and a live PostgreSQL template of
    `count_distinct(a, b)` under GROUP BY and a WHERE header parameter bind it
    and render the emitted SQL byte for byte."""
    from _pietto_sql_query_parameters import parameterized_case
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    body = (
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    group by flag\n    select:\n        flag\n"
        "        pairs = count_distinct(id, flag)\n"
    )
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == template.artifact.rendered.sql
        assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
        assert b"COUNT(DISTINCT CASE WHEN " in bound.artifact.rendered.sql
        assert bound.arguments == (3,)


def test_a_first_and_last_template_binds_its_header_read(tmp_path):
    """A loaded compiled and a live PostgreSQL template of `first` and `last`
    under GROUP BY and a WHERE header parameter bind it and render the emitted
    SQL byte for byte; `last` keeps its flipped key directions."""
    import _pietto_sql_emission as emission
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    item = emission.parameterized_fixture(
        "postgres",
        "query result(low: Int):\n    from rows\n    where id > low\n"
        "    group by flag\n    select:\n        flag\n"
        "        f = first(text, order by ratio desc, id)\n"
        "        l = last(money, order by id)\n",
    )
    source = item["source"].replace(
        "    ratio: Float\n", "    ratio: Float\n    row_key = unique(id)\n", 1
    )
    _, outcome = emission.build_case(tmp_path, source, item["contract"], item["policy"])
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(outcome.artifact)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, (3,), strict=True))
        )
        assert bound.artifact.rendered.sql == template.artifact.rendered.sql
        assert bound.artifact.rendered.sql == outcome.artifact.rendered.sql
        assert (
            b'(ARRAY_AGG("t1"."c2" ORDER BY "t1"."c4" DESC, "t1"."c0" ASC))[1] '
            b'AS "c1", (ARRAY_AGG("t1"."c3" ORDER BY "t1"."c0" DESC))[1] AS "c2"'
        ) in bound.artifact.rendered.sql
        assert bound.arguments == (3,)


# Phase70 S11 x S10/S12/S14: header reads inside lets with capture lines.
HEADER_IN_CAPTURES = """query result(cut: Int, hi: Int | None):
    let later:
        capture lhs
        from rhs
        where rhs.id > lhs.id and rhs.id < hi and rhs.id != 100
        select:
            later_id = id
        order by:
            id desc
        limit 2
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > cut
        select:
            id
    from lhs
    let l = later
    left join l on l.later_id > cut
    where exists matched and lhs.id < hi
    select:
        id = lhs.id
        later_id = l.later_id
"""


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_header_reads_inside_capturing_lets_round_trip_and_bind_in_order(
    tmp_path, target
):
    """A LATERAL top-k let and an EXISTS-read let read the header; the v2
    root carries their reads, decodes byte for byte and binds them in the
    template's placeholder order, the slot between them included."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
    )

    item = probe.join_witness(target, HEADER_IN_CAPTURES, policy="bind_safe_literals")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    assert json.loads(built.payload)["format"] == wire.PARAMETERIZED_FORMAT
    assert wire.encode(wire.decode(built.payload)) == built.payload
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == outcome.artifact.rendered.sql
    assert [(p.name, p.nullable) for p in template.parameters] == [
        ("cut", False),
        ("hi", True),
    ]
    literals = tuple(
        (s, s.original.site.position.literal.value) for s in template.slots
    )
    for values, arguments in (
        # PostgreSQL: hi=$1 (let later), 100=$2, cut=$3 (ON, let matched),
        # hi again; MySQL: one marker per read in rendering order.
        ((3, 7), (7, 100, 3) if target == "postgres" else (7, 100, 3, 3, 7)),
        (
            (3, None),
            (None, 100, 3) if target == "postgres" else (None, 100, 3, 3, None),
        ),
    ):
        bound = bind_values(
            template, literals, tuple(zip(template.parameters, values, strict=True))
        )
        assert bound.artifact.rendered.sql == template.artifact.rendered.sql
        assert bound.arguments == arguments
    # A re-pinned root whose first two native uses trade slots is refused.
    description = built.root.description
    first, second = [r for r in description.records if r.address.kind == "native_use"][
        :2
    ]

    def change(record):
        if record is first:
            return _set(record, "slot", second.get("slot"))
        if record is second:
            return _set(record, "slot", first.get("slot"))
        return record

    forged = wire.Description(
        description.compatibility,
        description.producer,
        description.query,
        tuple(
            (member, tuple(change(r) for r in records))
            for member, records in description.members
        ),
    )
    raw = wire.encode(forged)
    with pytest.raises(wire.CompiledError):
        prepare_compiled_template(
            load_compiled(
                raw,
                expected_pin=wire.content_pin(raw),
                accepted_producer=forged.producer,
                accepted_compatibility=forged.compatibility,
            )
        )


# Phase70 S11 x S10/S14: binding obligations inside lets with capture lines
# (an Int sum or difference, a Text call) are checked for each binding.
OBLIGATIONS_IN_CAPTURES = """query result(cut: Int, tag: Text | None):
    let early:
        capture lhs
        from rhs
        where rhs.id > cut + 1 and rhs.id < lhs.id
        select:
            id
    let near:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            v = lower(tag)
    let later:
        capture lhs
        from rhs
        where rhs.id > lhs.id and rhs.id > cut - 3
        select:
            id
    let other:
        capture lhs
        from rhs
        where rhs.id == lhs.id and rhs.id != cut + 2
        select:
            id
    from lhs
    where exists early and lhs.id in other and lhs.id not in later
    select:
        id
        v = scalar near.v
"""
OBLIGATION_ARGUMENTS = {
    ("postgres", "preserve_literals"): lambda cut, tag: (cut, tag),
    ("postgres", "bind_safe_literals"): lambda cut, tag: (cut, 1, 2, 3, tag),
    ("mysql", "preserve_literals"): lambda cut, tag: (cut, cut, cut, tag),
    ("mysql", "bind_safe_literals"): lambda cut, tag: (cut, 1, cut, 2, cut, 3, tag),
}


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_obligations_inside_capturing_lets_are_checked_for_each_binding(
    tmp_path, target, policy
):
    """`exists`, `scalar`, `in` and `not in` reads render their lets inline;
    each deferred check there is imaged in the bound statement like any
    other, so a value is refused only when its own result leaves the range."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
    )

    item = probe.join_witness(target, OBLIGATIONS_IN_CAPTURES, policy=policy)
    contract = json.loads(item["contract"])
    if policy == "preserve_literals":
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    _, outcome = probe.build_case(
        tmp_path, item["source"], json.dumps(contract), item["policy"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    literals = tuple(
        (s, s.original.site.position.literal.value) for s in template.slots
    )
    expected = OBLIGATION_ARGUMENTS[target, policy]
    for cut, tag in ((5, "Ab"), (0, None), (2**63 - 3, "x"), (-(2**63) + 3, None)):
        bound = bind_values(
            template,
            literals,
            tuple(zip(template.parameters, (cut, tag), strict=True)),
        )
        assert bound.arguments == expected(cut, tag)
    # `cut + 2` and `cut - 3` leave the signed 64-bit range one step further.
    for cut in (2**63 - 2, -(2**63) + 2):
        with pytest.raises(ValueError, match="^BINDING_INVALID$"):
            bind_values(
                template,
                literals,
                tuple(zip(template.parameters, (cut, "x"), strict=True)),
            )


# Phase70 S16: header reads in capture-free lets that a JOIN reads and that
# `exists`, `in` and `scalar` read, beside a read in the entry WHERE.
HEADER_LETS_READS_JOIN = """query result(low: Int, hi: Int | None):
    let near:
        from rhs
        where id > low
        select:
            id
            key
    let keys:
        from rhs
        where key < hi
        select:
            key
    let top:
        from rhs
        where id > low
        select:
            n = count()
    from lhs
    let r = near
    inner join r on lhs.id == r.id
    where exists keys and lhs.key in keys and lhs.id <= scalar top.n and lhs.id < hi
    select:
        id = lhs.id
        k = r.key
"""


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_header_reads_in_joined_and_read_lets_round_trip_and_bind(tmp_path, target):
    """The v2 root carries the reads of the JOIN target's let, the read lets
    and the entry body; it decodes byte for byte and binds them in the
    template's placeholder order (PostgreSQL reuses `$1` and `$2`)."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
    )

    item = probe.join_witness(
        target, HEADER_LETS_READS_JOIN, policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    # The JOIN reads the CTE of `near`; `exists` and `in` read that of `keys`.
    assert sql.count(b" INNER JOIN ") == sql.count(b"EXISTS (SELECT 1 FROM ") == 1
    assert sql.count(b" IN (SELECT ") == 1
    built = build_compiled(outcome.artifact)
    assert json.loads(built.payload)["format"] == wire.PARAMETERIZED_FORMAT
    assert wire.encode(wire.decode(built.payload)) == built.payload
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == sql
    assert [(p.name, p.nullable) for p in template.parameters] == [
        ("low", False),
        ("hi", True),
    ]
    for values in ((2, 9), (-1, None)):
        bound = bind_values(
            template, (), tuple(zip(template.parameters, values, strict=True))
        )
        assert bound.artifact.rendered.sql == sql
        # `near`, `keys`, `top`, then the entry WHERE.
        assert bound.arguments == (values if target == "postgres" else values * 2)


@pytest.fixture(scope="module", params=("postgres", "mysql"))
def modern_predicate_bundle(tmp_path_factory, request):
    """One immutable source/compiled acquisition per target for call-boundary checks."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled

    target = request.param
    item = probe.join_witness(target, "")
    source = f"""shape Row:
    id: Int
    key: Int | None
source lhs: Row = {target}.table("lhs")
source rhs: Row = {target}.table("rhs")
relationship Active(l: Row, r: Row):
    l.id == r.id and r.id > 0
relationship Either(l: Row, r: Row):
    l.id == r.id or l.key == r.key
query result:
    from lhs
    inner join rhs on Active(lhs, rhs) and (Either(lhs, rhs) or not Active(lhs, rhs))
    where Active(lhs, rhs)
    select:
        id = lhs.id
        flag = Active(lhs, rhs)
        coalesced = coalesce(rhs.key, lhs.id)
        conditional = lhs.id if rhs.key is None else rhs.key
        membership = lhs.id in (1, 2)
        floating = Float(lhs.id)
"""
    _, outcome = probe.build_case(
        tmp_path_factory.mktemp("modern-compiled-" + target),
        source,
        item["contract"],
        item["policy"],
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    return build_compiled(outcome.artifact), outcome.artifact


def test_compiled_modern_calls_keep_context_and_occurrence(modern_predicate_bundle):
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    built, original = modern_predicate_bundle
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    records = loaded.records
    calls = tuple(r for r in records.values() if r.address.kind == "predicate_call")
    assert [call.get("role") for call in calls] == ["on", "on", "on", "where", "select"]
    assert [len(call.get("equalities")) for call in calls] == [1, 0, 0, 1, 0]
    assert wire.predicate_equalities(records, records[calls[3].get("owner")]) == ()
    join = records[calls[0].get("owner")]
    assert join.get("equalities") == ()
    assert tuple(
        item.address for item in wire.predicate_equalities(records, join)
    ) == calls[0].get("equalities")
    left, right = (records[a] for a in calls[0].get("arguments"))
    assert left.get("use") != right.get("use")
    assert (left.get("binding"), right.get("binding")) == (0, 1)
    template = prepare_compiled_template(loaded)
    assert template.artifact.rendered.sql == original.rendered.sql


@pytest.mark.parametrize(
    "mutation", ("drop_equality", "or_equality", "argument_ports", "argument_ordinal")
)
def test_compiled_modern_call_forgery_is_refused(modern_predicate_bundle, mutation):
    built, _ = modern_predicate_bundle
    description = built.root.description
    records = built.root.records
    calls = tuple(r for r in records.values() if r.address.kind == "predicate_call")
    original = calls[0]
    field, replacement = "equalities", ()
    category = "PREDICATE_EQUALITIES"
    if mutation == "or_equality":
        original = calls[1]
        replacement = calls[0].get("equalities")
    elif mutation in ("argument_ports", "argument_ordinal"):
        original = records[calls[0].get("arguments")[0]]
        if mutation == "argument_ports":
            field = "ports"
            replacement = records[calls[0].get("arguments")[1]].get("ports")
            category = "PREDICATE_BINDING"
        else:
            field, replacement, category = "binding", 1, "PREDICATE_BINDING"
    forged = wire.Description(
        description.compatibility,
        description.producer,
        description.query,
        tuple(
            (
                name,
                tuple(
                    _set(record, field, replacement) if record is original else record
                    for record in members
                ),
            )
            for name, members in description.members
        ),
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_" + category + "$"):
        verify_description(forged)


def test_a_description_of_an_earlier_version_is_refused(modern_predicate_bundle):
    description = modern_predicate_bundle[0].root.description
    assert description.compatibility[:4] == wire.VERSIONS
    schema, semantic, occurrence, profile = wire.VERSIONS
    earlier = (schema - 1, semantic, occurrence - 1, profile)
    for labels in (
        earlier,
        (*wire.VERSIONS[:2], *earlier[2:]),
        (*earlier[:2], *wire.VERSIONS[2:]),
    ):
        forged = wire.Description(
            (*labels, description.compatibility[4]),
            description.producer,
            description.query,
            description.members,
        )
        with pytest.raises(wire.CompiledError, match="^COMPILED_COMPATIBILITY$"):
            verify_description(forged)


@pytest.mark.parametrize(
    "field,value",
    (
        ("logical", ("collection", "non_null")),
        ("logical", ("Float", "nullable")),
        ("meaning", "UUID"),
    ),
)
def test_an_output_record_repeats_its_port_exactly(
    modern_predicate_bundle, field, value
):
    """No reader reads an output record's own type; a bundle whose output
    record disagrees with its port is refused at load."""
    from pietto._project.project_compiled_loading import load_compiled

    built, _ = modern_predicate_bundle
    records = built.root.records
    first = records[wire.Address("output", 0)]
    assert (first.get("logical"), first.get("meaning")) == (
        records[first.get("port")].get("logical"),
        None,
    )
    raw = wire.encode(
        _forged(
            built.root.description,
            lambda r: _set(r, field, value) if r.address == first.address else r,
        )
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_OUTPUT_PORT$"):
        load_compiled(
            raw,
            expected_pin=wire.content_pin(raw),
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "body,expanded,concrete",
    (
        ("r.flag and r.flag", "lhs.flag and lhs.flag", True),
        ("r.id == r.id", "lhs.id == lhs.id", False),
    ),
    ids=("bool_and_execution_boundary", "comparison_semantic_boundary"),
)
def test_predicate_count_keeps_the_expanded_aggregate_execution_boundary(
    tmp_path, target, body, expanded, concrete
):
    import _pietto_sql_emission as probe
    from pietto._project.aggregate_grouped_schema import (
        ProjectAggregateExpressionAnalysis,
    )
    from pietto._project.project_sql_plan import ProjectSQLPlan, predicate_expression

    item = probe.join_witness(target, "")
    contract = json.loads(item["contract"])
    contract["sources"] = contract["sources"][:1]
    flag = next(
        field
        for field in json.loads(probe.fixture(target)["contract"])["sources"][0][
            "fields"
        ]
        if field["name"] == "flag"
    )
    flag["ordinal"] = 2
    contract["sources"][0]["fields"].append(flag)
    header = f"""shape Row:
    id: Int
    key: Int | None
    flag: Bool | None
source lhs: Row = {target}.table("lhs")
relationship Positive(r: Row):
    {body}
query result:
    from lhs
    select:
        total = count(ARGUMENT)
"""
    outcomes = []
    # Both targets count a Bool row expression as a LET would
    # lower it.
    emitted = concrete
    for name, argument in (("call", "Positive(lhs)"), ("expanded", expanded)):
        checked, outcome = probe.build_case(
            tmp_path / name,
            header.replace("ARGUMENT", argument),
            json.dumps(contract),
            item["policy"],
        )
        assert checked.verified is concrete
        if emitted:
            assert outcome.status == "VERIFIED" and outcome.artifact is not None
            outcomes.append(outcome.artifact.rendered.sql)
        else:
            assert outcome.artifact is None
            assert outcome.status == "BLOCKED"
            outcomes.append(tuple((b.code, b.detail) for b in outcome.blockers))
        if not concrete:
            continue
        assert isinstance(checked.plan, ProjectSQLPlan)
        calls = tuple(
            (site, record)
            for site in checked.plan.expression_sites
            if (record := predicate_expression(site)) is not None
        )
        if name == "call":
            assert len(calls) == 1
            site, record = calls[0]
            assert site.role.value == "aggregate_argument"
            assert record.parent is not None
            assert len(record.calls) == 1
            assert record.calls[0] is record.parent.calls[0]
            assert record.argument_bindings[0] is record.parent.argument_bindings[0]
            assert isinstance(site.evidence, ProjectAggregateExpressionAnalysis)
            assert record.expression is site.evidence.effective_argument
        else:
            assert calls == ()
    assert outcomes[0] == outcomes[1]
    if emitted:
        q = '"' if target == "postgres" else "`"
        assert (
            f"COUNT(({q}s0{q}.{q}flag value{q} AND {q}s0{q}.{q}flag value{q}))"
        ).encode() in outcomes[0]


@pytest.fixture(scope="module", params=("postgres", "mysql"))
def any_retained_bundle(tmp_path_factory, request):
    """Share the immutable selected/retained acquisition; mutations stay local."""
    body = """    from lhs
    where any(Same(lhs, candidate) for candidate in rhs)
    let candidate = rhs
    inner join candidate on Same(lhs, candidate)
    let bounded = ranked
    inner join bounded on candidate.id == bounded.id
    where not any(Same(candidate, candidate) for candidate in rhs)
    select:
        id = lhs.id
        matched = candidate.id
"""
    return _retained_any_bundle(
        tmp_path_factory.mktemp("any-retained-" + request.param), request.param, body
    )


@pytest.fixture(scope="module", params=("postgres", "mysql"))
def any_value_retained_bundle(tmp_path_factory, request):
    body = """    from lhs
    let candidate = rhs
    inner join candidate on Same(lhs, candidate) and any(Same(lhs, local_row) and local_row.id == candidate.id for local_row in rhs)
    let bounded = ranked
    inner join bounded on candidate.id == bounded.id
    let found = any(Same(candidate, local_row) for local_row in rhs)
    where lhs.key is None or any(Same(lhs, local_row) for local_row in rhs) or found
    select:
        id = lhs.id
        found
        again = not found
        nested = any(any(Same(parent_row, child_row) and child_row.id == lhs.id for child_row in rhs) for parent_row in rhs)
        nullable_flag = any(local_row.key == lhs.key for local_row in ranked)
        null_flag = any(None for local_row in ranked)
"""
    return _retained_any_bundle(
        tmp_path_factory.mktemp("any-value-retained-" + request.param),
        request.param,
        body,
    )


def _retained_any_bundle(directory, target, body):
    from dataclasses import replace
    import _pietto_sql_emission as probe
    from pietto.ast_nodes import AuthoredJoinKind
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import (
        ProjectSingleMatchRequest,
        ProjectSingleMatchAssessment,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_emission import emit_project_sql

    item = probe.join_witness(target, "")
    header = f"""shape Row:
    id: Int
    key: Int | None
source lhs: Row = {target}.table("lhs")
source rhs: Row = {target}.table("rhs")
relationship Same(left: Row, right: Row):
    left.id == right.id
table ranked:
    from rhs
    where any(Same(local_row, local_row) for local_row in rhs)
    select:
        id = rhs.id
        key = rhs.key
    limit 1
"""
    source = header + "".join(
        f"query {name}:\n" + body for name in ("result", "unused_a", "unused_b")
    )
    checked, _ = probe.build_case(
        directory,
        source,
        item["contract"],
        item["policy"],
    )
    completed = checked.completed
    requests = []
    for condition in completed.roots.join_conditions.entries:
        if (
            condition.use.clause.kind is not AuthoredJoinKind.INNER
            or condition.use.target_binding.name != "bounded"
        ):
            continue
        request = ProjectSingleMatchRequest(
            owner=condition.use.owner, use=condition.use, condition=condition
        )
        assessment = ProjectSingleMatchAssessment(
            root=completed.effective_outputs, request=request
        )
        requests.append(replace(request, input_pairs=assessment.input_pairs))
    assert len(requests) == 3
    completed = with_project_single_match_requests(completed, tuple(requests))
    ir = build_project_query_block_ir(completed)
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(ir)
    )
    (selected,) = tuple(o for o in ir.owners if o.definition.name == "result")
    plan = build_project_sql_plan(
        completed, bundle, selected, literal_policy=checked.literal_policy
    )
    verified = verify_project_sql_plan(
        plan, completed, bundle, selected, literal_policy=checked.literal_policy
    )
    emitted = emit_project_sql(verified, item["contract"].encode())
    assert emitted.status == "VERIFIED", {
        "plan_issues": verified.issues,
        "cli_errors": emitted.cli_errors,
        "diagnostics": emitted.diagnostics,
        "blockers": emitted.blockers,
    }
    assert emitted.artifact is not None
    return build_compiled(emitted.artifact), emitted.artifact


def test_compiled_any_retains_siblings_calls_and_hidden_binding_gaps(
    any_retained_bundle,
):
    from pietto._project.project_execution_template import prepare_compiled_template
    from pietto._project.project_sql_emission import CompiledEmissionArtifact

    built, original = any_retained_bundle
    records = built.root.records
    entry = records[built.root.description.query]
    assert len(entry.get("retained")) == 2
    assert len(entry.get("requests")) == 3
    filters = tuple(r for r in records.values() if r.address.kind == "any_filter")
    by_owner = {}
    for record in filters:
        join = records[record.get("join")]
        owner = records[join.get("owner")].get("label")
        by_owner.setdefault(owner, []).append(record)
    assert tuple(by_owner) == ("result", "unused_a", "unused_b")
    for owner_filters in by_owner.values():
        (record,) = owner_filters
        assert record.get("prefix") == 0
        assert record.get("context") == "join_filter"
        join = records[record.get("join")]
        assert join.get("kind") == "semi"
        (call,) = wire.predicate_calls(records, join)
        arguments = tuple(records[a] for a in call.get("arguments"))
        assert arguments[-1].get("binding") == 1
        assert len(call.get("equalities")) == 1
        assert join.get("equalities") == ()
    values = tuple(r for r in records.values() if r.address.kind == "any_value")
    (ranked,) = tuple(
        r.address
        for r in records.values()
        if r.address.kind == "declaration" and r.get("label") == "ranked"
    )
    (shared,) = tuple(
        r
        for r in values
        if records[records[r.get("read")].get("consumer")].get("owner") == ranked
    )
    assert shared.get("context") == "where" and shared.get("prefix") == 0
    assert len(values) == 4
    inner = tuple(
        r
        for r in records.values()
        if r.address.kind == "join"
        and r.get("kind") == "inner"
        and wire.predicate_calls(records, r)
    )
    assert len(inner) == 3
    for join in inner:
        (call,) = wire.predicate_calls(records, join)
        assert tuple(records[a].get("binding") for a in call.get("arguments")) == (0, 2)
        owner_filters = by_owner[records[join.get("owner")].get("label")]
        (tail,) = tuple(
            records[r.get("read")]
            for r in values
            if records[records[r.get("read")].get("consumer")].get("owner")
            == join.get("owner")
        )
        (tail_call,) = wire.predicate_calls(records, records[tail.get("consumer")])
        arguments = tuple(records[a] for a in tail_call.get("arguments"))
        assert tuple(argument.get("binding") for argument in arguments) == (0, 0)
        assert arguments[0].get("use") == arguments[1].get("use") == tail.address
        assert arguments[0].get("ports") == arguments[1].get("ports")
        assert tail_call.get("equalities") == ()
        right_uses = (
            *tuple(
                records[stage.get("inputs")[1]]
                for stage in (
                    records[owner_filters[0].get("join")],
                    join,
                )
            ),
            tail,
        )
        assert len({use.address for use in right_uses}) == 3
        assert len({use.get("producer") for use in right_uses}) == 1
    assert len({r.get("location") for r in filters}) == 3
    assert len({r.get("location") for r in values if r is not shared}) == 3
    loaded = prepare_compiled_template(built.root)
    assert isinstance(loaded.artifact, CompiledEmissionArtifact)
    assert loaded.artifact.rendered.sql == original.rendered.sql
    assert len(loaded.artifact.request.plan.all_single_matches) == 3
    assert len(loaded.artifact.request.plan.single_matches) == 1


@pytest.mark.parametrize(
    "mutation", ("stage", "prefix", "context", "location", "sibling")
)
def test_compiled_any_mapping_forgery_is_refused(any_retained_bundle, mutation):
    from dataclasses import replace

    built, _ = any_retained_bundle
    records = built.root.records
    filters = tuple(r for r in records.values() if r.address.kind == "any_filter")
    original = filters[0]
    field, replacement, category = "prefix", 1, "ANY_PREFIX"
    if mutation == "stage":
        field, category = "join", "ANY_STAGE"
        replacement = next(
            r.address
            for r in records.values()
            if r.address.kind == "join" and r.get("kind") == "inner"
        )
    elif mutation == "context":
        field, replacement, category = "context", "where", "ANY_CONTEXT"
    elif mutation == "location":
        field, replacement, category = (
            "location",
            filters[-1].get("location"),
            "ANY_LOCATION",
        )
    elif mutation == "sibling":
        field, replacement, category = "join", filters[2].get("join"), "ANY_STAGE"
    forged = replace(
        built.root.description,
        members=tuple(
            (
                name,
                tuple(
                    _set(record, field, replacement) if record is original else record
                    for record in members
                ),
            )
            for name, members in built.root.description.members
        ),
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_" + category + "$"):
        verify_description(forged)


def test_compiled_any_export_refuses_omitted_authored_inventory(any_retained_bundle):
    from pietto._project.project_compiled_verification import verify_any_export

    built, original = any_retained_bundle
    omitted = {
        address: record
        for address, record in built.root.records.items()
        if address.kind != "any_filter"
    }
    with pytest.raises(wire.CompiledError, match="^COMPILED_EXPORT_ANY_INVENTORY$"):
        verify_any_export(omitted, original.request.plan)


def test_compiled_any_values_preserve_selected_and_retained_lexical_occurrences(
    any_value_retained_bundle,
):
    from pietto._project.project_execution_template import prepare_compiled_template
    from pietto._project.project_sql_emission import CompiledEmissionArtifact
    from pietto._project.project_sql_plan_expressions import ProjectSQLAny

    built, original = any_value_retained_bundle
    records = built.root.records
    values = tuple(r for r in records.values() if r.address.kind == "any_value")
    per_owner = {}
    for value in values:
        read = records[value.get("read")]
        consumer = records[read.get("consumer")]
        owner = records[consumer.get("owner")].get("label")
        per_owner.setdefault(owner, []).append(value)
        operation = records[read.get("operation")]
        assert operation.get("operator") == ("exists", "exists")
        assert len(operation.get("operands")) == 1
        assert operation.get("logical") == ("Bool", "non_null")
    assert tuple(per_owner) == ("ranked", "result", "unused_a", "unused_b")
    (shared,) = per_owner.pop("ranked")
    assert shared.get("context") == "where" and shared.get("prefix") == 0
    selected = tuple(
        e for e in original.request.plan.expressions if type(e) is ProjectSQLAny
    )
    assert len(per_owner["result"]) + 1 == len(selected)
    for items in per_owner.values():
        assert {value.get("context") for value in items} == {
            "on",
            "let",
            "where",
            "select",
            "any",
        }
        assert len({value.get("read") for value in items}) == len(items)
        assert len({value.get("location") for value in items}) == len(items)
        assert all(
            value.get("prefix") == (1 if value.get("context") == "on" else 2)
            for value in items
        )
    for join in (r for r in records.values() if r.address.kind == "join"):
        calls = wire.predicate_calls(records, join)
        if not calls:
            # `candidate.id == bounded.id`, written by hand.
            assert len(wire.predicate_equalities(records, join)) == 1
            continue
        assert len(calls) == 2
        assert tuple(len(call.get("equalities")) for call in calls) == (1, 0)
        assert len(wire.predicate_equalities(records, join)) == 1
    template = prepare_compiled_template(built.root)
    assert isinstance(template.artifact, CompiledEmissionArtifact)
    assert template.artifact.rendered.sql == original.rendered.sql
    assert len(template.artifact.request.plan.all_single_matches) == 3
    assert len(template.artifact.request.plan.single_matches) == 1


@pytest.mark.parametrize(
    "mutation", ("sibling_input", "missing_values", "lost_predicate")
)
def test_compiled_any_value_scope_forgery_is_refused(
    any_value_retained_bundle, mutation
):
    from dataclasses import replace

    built, _ = any_value_retained_bundle
    records = built.root.records
    changed = None
    category = "ANY_SCOPE"
    if mutation == "sibling_input":
        original = next(
            r
            for r in records.values()
            if r.address.kind == "read" and r.get("role") == "any"
        )
        use = records[original.get("use")]
        consumer_owner = records[use.get("consumer")].get("owner")
        sibling = next(
            r
            for r in records.values()
            if r.address.kind == "expression_block_use"
            and r.get("producer") == use.get("producer")
            and records[r.get("consumer")].get("owner") != consumer_owner
        )
        changed = _set(original, "use", sibling.address)
    elif mutation == "lost_predicate":
        original = next(
            r
            for r in records.values()
            if r.address.kind == "operation"
            and r.get("operator") == ("exists", "exists")
            and r.get("operands")
        )
        changed = _set(original, "operands", ())
        category = "ANY_READ_INVENTORY"
    else:
        category = "ANY_VALUE_INVENTORY"
    forged = replace(
        built.root.description,
        members=tuple(
            (
                name,
                tuple(
                    changed
                    if changed is not None and r.address == changed.address
                    else r
                    for r in members
                    if mutation != "missing_values" or r.address.kind != "any_value"
                ),
            )
            for name, members in built.root.description.members
        ),
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_" + category + "$"):
        verify_description(forged)


@pytest.mark.parametrize("kind", ("conditional", "cast", "membership"))
def test_join_projection_operations_require_closed_operand_lists(
    modern_predicate_bundle, kind
):
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    built, _ = modern_predicate_bundle
    operation = next(
        record
        for record in built.root.description.records
        if record.address.kind == "operation" and record.get("operator")[0] == kind
    )
    operands = operation.get("operands")
    malformed = (
        operands[:-1]
        if kind == "conditional"
        else (*operands, operands[0])
        if kind == "cast"
        else ()
    )
    changed = _forged(
        built.root.description,
        lambda record: (
            _set(record, "operands", malformed) if record is operation else record
        ),
    )
    raw = wire.encode(changed)
    with pytest.raises(wire.CompiledError):
        prepare_compiled_template(
            load_compiled(
                raw,
                expected_pin=wire.content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )
        )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("variant", ("timestamp_union_all", "timestamp_union_distinct"))
def test_timestamp_set_export_keeps_kind_quantifier_and_operand_order(
    tmp_path, target, variant
):
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_verification import verify_export

    item = probe.fixture(target, "S_set_domains", variant)
    _, outcome = probe.build_case(
        tmp_path / "source", item["source"], item["contract"], item["policy"]
    )
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    operation = next(
        r for r in built.root.description.records if r.address.kind == "set"
    )
    for field, value in (
        ("kind", "intersect"),
        ("quantifier", "distinct" if variant.endswith("_all") else "all"),
        ("operands", tuple(reversed(operation.get("operands")))),
    ):
        changed = _forged(
            built.root.description,
            lambda r: _set(r, field, value) if r is operation else r,
        )
        with pytest.raises(wire.CompiledError):
            verify_export(changed, outcome.artifact)


@pytest.mark.parametrize(
    "target,case,variant",
    (
        ("postgres", "F_float_values", "fi_distinct"),
        ("postgres", "F_float_values", "fe_all"),
        ("mysql", "S_set_domains", "float_union_all"),
    ),
)
def test_float_set_export_keeps_kind_quantifier_and_operand_order(
    tmp_path, target, case, variant
):
    """A PostgreSQL Float INTERSECT/EXCEPT exports as authored; a MySQL Float
    UNION ALL forged into an INTERSECT, the form MySQL refuses, is refused by
    the export check and, re-pinned, by the compiled set-domain law."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_verification import verify_export
    from pietto._project.project_completed_semantics import derive_compiled_semantics

    item = probe.fixture(target, case, variant)
    _, outcome = probe.build_case(
        tmp_path / "source", item["source"], item["contract"], item["policy"]
    )
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    verify_export(built.root.description, outcome.artifact)
    operation = next(
        r for r in built.root.description.records if r.address.kind == "set"
    )
    forgeries = (
        (("kind", "intersect"),)
        if target == "mysql"
        else (
            ("kind", "union"),
            (
                "quantifier",
                "all" if operation.get("quantifier") != "all" else "distinct",
            ),
            ("operands", tuple(reversed(operation.get("operands")))),
        )
    )
    for field, value in forgeries:
        changed = _forged(
            built.root.description,
            lambda r: _set(r, field, value) if r is operation else r,
        )
        with pytest.raises(wire.CompiledError):
            verify_export(changed, outcome.artifact)
        if target == "mysql":
            raw = wire.encode(changed)
            with pytest.raises(wire.CompiledError, match="^COMPILED_SET_DOMAIN$"):
                derive_compiled_semantics(
                    load_compiled(
                        raw,
                        expected_pin=wire.content_pin(raw),
                        accepted_producer=built.producer,
                        accepted_compatibility=built.compatibility,
                    ),
                    (),
                )


def test_a_typed_root_records_each_parameter_kind_and_its_decimal_carrier(tmp_path):
    """A header record names its tag and, for a Decimal
    only, the declared (precision, scale); the loaded template reads both. A
    record of the earlier five-field shape (a bundle of an earlier release)
    never decodes, and no record is migrated."""
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    built = _parameterized(tmp_path, "postgres", "typed_timestamp")
    description = built.root.description
    header = [r for r in description.records if r.address.kind == "parameter"]
    assert wire.FIELDS["parameter"][-1] == "decimal"
    assert [r.values[2:] for r in header] == [
        ("since", "Timestamp", False, None),
        ("day", "Date", False, None),
        ("floor", "Decimal", False, (9, 2)),
    ]
    loaded = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert [(p.name, p.tag, p.nullable, p.decimal) for p in loaded.parameters] == [
        ("since", "Timestamp", False, None),
        ("day", "Date", False, None),
        ("floor", "Decimal", False, (9, 2)),
    ]
    _since, day, floor = header
    for change in (
        lambda r: _set(r, "decimal", None) if r is floor else r,
        lambda r: _set(r, "decimal", (2, 3)) if r is floor else r,
        lambda r: _set(r, "decimal", (66, 2)) if r is floor else r,
        lambda r: _set(r, "decimal", (9, 2)) if r is day else r,
        lambda r: _set(r, "tag", "Json") if r is day else r,
    ):
        with pytest.raises(wire.CompiledError, match="^COMPILED_PARAMETER$"):
            verify_description(_forged(description, change))
    document = json.loads(built.payload)
    for _, records in document["members"]:
        for record in records:
            if record[0] == "parameter":
                record[2] = record[2][:-1]
    old = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()
    with pytest.raises(wire.CompiledError, match="^COMPILED_FIELDS$"):
        wire.decode(old)


def test_a_mysql_typed_parameter_outside_its_cells_never_replays(tmp_path):
    """The family's own carriers bound the header tags a bundle may name:
    MySQL's admit Decimal, Date and Timestamp (S09) and no UUID (D77.07).
    Compiled replay then derives the cells from the records, so `low`
    relabelled as Date or Decimal, read in `low + 1` and against Int fields,
    fails replay, its template and load_bundle."""
    built = _parameterized(tmp_path, "mysql", "bind")
    description = built.root.description
    low = next(r for r in description.records if r.address.kind == "parameter")
    for tag, decimal in (("Date", None), ("Decimal", (9, 2)), ("UUID", None)):
        changed = _forged(
            description,
            lambda r: _set(_set(r, "tag", tag), "decimal", decimal) if r is low else r,
        )
        if tag == "UUID":
            with pytest.raises(wire.CompiledError, match="^COMPILED_PARAMETER$"):
                verify_description(changed)
            continue
        verify_description(changed)
        _assert_bundle_loads_or_refused(built, wire.encode(changed), True)


@pytest.mark.parametrize(
    "expression",
    [
        "money * factor",
        "factor * money",
        "value * id",
        "id * value",
        "value * factor",
        "-value",
    ],
)
def test_decimal_int_parameters_survive_compiled_replay(tmp_path, expression):
    from _pietto_sql_query_parameters import typed_case
    from pietto._project.project_sql_emission import serialize_project_sql_emission
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from _pietto_sql_emission_portable import (
        export_emission_observation,
    )
    from _pietto_sql_emission_portable import ObservationStatus

    body = (
        "query result(value: Decimal(9, 2), factor: Int):\n    from rows\n    select:\n        total = "
        + expression
        + "\n"
    )
    checked, outcome = typed_case(tmp_path, "postgres", body)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    doc = json.loads(serialize_project_sql_emission(outcome))
    assert doc["columns"][0]["representation"]["storage"] == {
        "kind": "pg_numeric",
        "precision": 9 if expression == "-value" else 28,
        "scale": 2,
    }
    observed = export_emission_observation(artifact, artifact.request)
    # Header parameters retain their existing portable-observation boundary.
    assert observed.status is ObservationStatus.OUTSIDE_SCHEMA
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql == artifact.rendered.sql


def _document(outcome) -> dict[str, Any]:
    return json.loads(serialize_project_sql_emission(outcome))


@pytest.mark.parametrize(
    ("body", "carrier"),
    (
        (
            "query result(fee: Decimal(8, 3)):\n    from rows\n"
            "    select:\n        total = money + fee\n",
            (11, 3),
        ),
        (
            "query result(delta: Int):\n    from rows\n"
            "    select:\n        total = money + delta\n",
            (22, 2),
        ),
    ),
    ids=("different_decimal_scale", "int_parameter"),
)
def test_postgres_e9_parameter_pairs_change_the_decimal_carrier(
    tmp_path: Path, body: str, carrier: tuple[int, int]
) -> None:
    checked, outcome = typed_case(tmp_path, "postgres", body)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    document = _document(outcome)
    assert document["columns"][0]["representation"]["storage"] == {
        "kind": "pg_numeric",
        "precision": carrier[0],
        "scale": carrier[1],
    }
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


def _loaded(artifact):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled

    built = build_compiled(artifact)
    return load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )


class _CountedRecords:
    """Compiled records that count each lookup and each item they yield."""

    def __init__(self, records):
        self.records, self.count = records, 0

    def __getitem__(self, address):
        self.count += 1
        return self.records[address]

    def items(self):
        for item in self.records.items():
            self.count += 1
            yield item


class _CountedExpressions(tuple):
    """Plan expressions that count each item an iteration of them yields."""

    yielded = 0

    def __iter__(self):
        for item in super().__iter__():
            self.yielded += 1
            yield item


class _CountedPlan:
    """A plan whose expressions are _CountedExpressions; every other
    attribute is the plan's."""

    def __init__(self, plan):
        self.plan, self.expressions = plan, _CountedExpressions(plan.expressions)

    def __getattr__(self, name):
        return getattr(self.plan, name)


class _CountedDocument:
    """A pure observation document that counts each lookup, each reference
    ``all`` returns and each record of a pass over ``records``."""

    def __init__(self, doc):
        self.doc, self.count = doc, 0

    @property
    def records(self):
        self.count += len(self.doc.records)
        return self.doc.records

    def __getitem__(self, ref):
        self.count += 1
        return self.doc[ref]

    def all(self, kind):
        found = self.doc.all(kind)
        self.count += len(found)
        return found


def _chained_lets(m):
    """m chained row lets renaming `text`, and m * m cells reading the last."""
    lets = "".join(
        f"    let a{i} = {'text' if i == 0 else f'a{i - 1}'}\n" for i in range(m)
    )
    items = "".join(f'        p{i} = lpad(a{m - 1}, 5, "0")\n' for i in range(m * m))
    return "table result:\n    from words\n" + lets + "    select:\n" + items


def _beside_a_capture(m):
    """One capture read and m * m cells beside it."""
    items = "".join(f'        a{i} = lpad(label, 5, "0")\n' for i in range(m * m))
    return (
        "table result:\n    let matched:\n        capture lhs\n        from rhs\n"
        '        where rhs.id == lhs.id and rhs.label == "x"\n'
        "        select:\n            id\n            label\n    from lhs\n"
        "    select:\n        m = scalar matched.label\n" + items
    )


@pytest.mark.parametrize(
    "world,family", (("words", _chained_lets), ("pair", _beside_a_capture))
)
def test_mysql_lpad_and_now_cells_are_derived_in_linear_work(
    tmp_path, monkeypatch, world, family
):
    """Compiled replay derives the cells with one pass over the records and
    the pure boundary with one pass over the document: the lookups per record
    and per node do not grow with the program, chained lets and m * m cells
    beside them or beside a capture read alike. Emission and its verification
    scan a plan's expressions once at most, however many calls ask."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows

    compiled, observed = {}, {}
    derive, place = pure._mysql_scalar_cells, rows.mysql_scalar_place
    plans: dict[int, _CountedPlan] = {}

    def counted_place(plan, expression):
        if id(plan) not in plans:
            plans[id(plan)] = _CountedPlan(plan)
        return place(plans[id(plan)], expression)

    for m in (4, 8, 16):
        plans.clear()
        with monkeypatch.context() as patch:
            patch.setattr(rows, "mysql_scalar_place", counted_place)
            _, outcome = lpad_now_world(tmp_path / f"m{m}", world, "mysql", family(m))
        assert plans
        assert sum(plan.expressions.yielded for plan in plans.values()) <= sum(
            len(plan.expressions) for plan in plans.values()
        )
        artifact = outcome.artifact
        assert artifact is not None, outcome.blockers
        loaded = _loaded(artifact)
        records = _CountedRecords(loaded.records)
        cells = rows.mysql_compiled_scalar_cells(
            records, loaded.records[loaded.description.query]
        )
        assert len(cells) == m * m
        compiled[m] = records.count / len(loaded.records)
        seen = []

        def counted(doc):
            document = _CountedDocument(doc)
            found = derive(document)
            seen.append((document.count / len(doc.records), len(found)))
            return found

        monkeypatch.setattr(pure, "_mysql_scalar_cells", counted)
        export = portable.export_emission_observation(artifact, artifact.request)
        assert export.canonical_bytes is not None
        assert pure.parse_emission_observation(export.canonical_bytes).status is (
            pure.Status.OK
        )
        monkeypatch.setattr(pure, "_mysql_scalar_cells", derive)
        ((observed[m], derived),) = seen
        assert derived == m * m
    for m in (8, 16):
        assert compiled[m] <= min(compiled[4] + 0.1, 1.3)
        assert observed[m] <= min(observed[4] + 0.1, 1.3)


# The refused bodies that another rule still refuses when every MySQL lpad
# and now() counts as in a cell: a width above 256, negative or without a
# bound, grouped and aggregate queries, an ORDER BY that names the item, a
# capturing let body with ORDER BY or LIMIT, and concat.
_LPAD_NOW_UNFORGEABLE = frozenset(
    {
        "width_257",
        "width_16384",
        "width_negative",
        "width_field",
        "width_def_300",
        "grouped_lpad",
        "grouped_now",
        "grouped_having",
        "grouped_without_aggregate",
        "order_names_the_item",
        "capture_body_order_limit",
        "capture_body_limit_only",
        "concat_of_lpad",
        "cells_beside_concat",
        "mixed_multi",
        "having_ungrouped",
        "global_aggregate",
        "global_aggregate_window",
        "grouped_window",
    }
)


def _in_a_cell(law):
    """``law`` with every MySQL lpad and now() it places counted as in a cell."""

    def opened(plan, expression, values):
        cell = law(plan, expression, values)
        if cell is None:
            return None
        if cell[0] == "lpad":
            return ("lpad", "select", ("field", "literal", "literal"))
        return ("now", "select", ())

    return opened


def _assert_every_reader_refuses(artifact, observed, loaded, detail):
    """Plain verification and the live template (plan), the pure boundary
    (document) and compiled replay and template (records) refuse a forged
    artifact, its observation and its loaded bundle."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import (
        BindingError,
        prepare_compiled_template,
        prepare_live_template,
    )
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    assert not verify_project_sql_emission(artifact, artifact.request).verified
    with pytest.raises(BindingError, match="^BINDING_ARTIFACT$"):
        prepare_live_template(artifact)
    if artifact.request.plan.parameters:
        # The pure boundary's closed schema has no header parameter.
        assert observed.status is portable.ObservationStatus.OUTSIDE_SCHEMA
    else:
        assert observed.canonical_bytes is not None
        refused = pure.parse_emission_observation(observed.canonical_bytes)
        assert (refused.status, refused.detail) == (
            pure.Status.INVALID_RELATION,
            detail,
        )
    values = tuple(value.value for value in artifact.fixed_values)
    for replay in (
        lambda: emit_compiled(loaded, values),
        lambda: prepare_compiled_template(loaded),
    ):
        with pytest.raises(wire.CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
            replay()


@pytest.mark.parametrize("shape", LPAD_NOW_REFUSALS)
def test_forged_mysql_lpad_and_now_outside_their_cells_fail_every_reader(
    tmp_path, monkeypatch, shape
):
    """An artifact of each refused body, emitted while every MySQL lpad and
    now() counts as in a cell, with its observation and compiled bundle
    exported under that law, fails each reader that derives the cells from
    its own record once the law is back; a body that another rule refuses
    has no artifact to forge. The pure boundary refuses the observation from
    its SQL alone too: with every call in a cell by its records, the
    rendered SQL is outside the cells, or another rule refuses it first."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows

    world, policy, body = LPAD_NOW_REFUSALS[shape]
    with monkeypatch.context() as patch:
        patch.setattr(rows, "mysql_scalar_cell", _in_a_cell(rows.mysql_scalar_cell))
        _, outcome = lpad_now_world(tmp_path, world, "mysql", body, policy)
        artifact = outcome.artifact
        if shape in _LPAD_NOW_UNFORGEABLE:
            assert artifact is None and outcome.blockers
            return
        assert artifact is not None, outcome.blockers
        observed = portable.export_emission_observation(artifact, artifact.request)
        loaded = _loaded(artifact)
    _assert_every_reader_refuses(artifact, observed, loaded, "mysql scalar cell")
    if observed.canonical_bytes is None:
        return
    monkeypatch.setattr(
        pure,
        "_mysql_scalar_cells",
        lambda doc: dict.fromkeys(
            (
                ref
                for ref in doc.all("sql_operation")
                if doc[ref]["operator"] in ("lpad", "now")
            ),
            ("now", "select", ()),
        ),
    )
    refused = pure.parse_emission_observation(observed.canonical_bytes)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        _REFUSED_BEFORE_THE_SQL.get(shape, "mysql scalar cell"),
    )


# The refused bodies whose observation another rule refuses before the
# rendered cells when every call is in a cell by its records.
_REFUSED_BEFORE_THE_SQL = {
    "nested_lpad": "C5 scalar token sequence",
    "text_capture_read": "inline unit",
    "width_conditional": "lpad realization",
}


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    "item",
    (
        'p = lpad(text, 257, "0")',
        'p = lpad(text, 300, "𝄞")',
        'p = lpad(text, 16383, "0")',
        'p = lpad(ntext, 1000, "雪")',
        'p = lpad("ab", 300, "雪")',
    ),
)
def test_forged_mysql_lpad_widths_above_256_fail_every_reader(
    tmp_path, monkeypatch, item, policy
):
    """An artifact emitted in a cell while the MySQL lpad width bound is
    raised, with its observation and compiled bundle exported under that
    bound, fails each reader once the bound is back, the pure boundary
    included: every reader keeps a MySQL width at 256 or below."""
    import _pietto_sql_emission_portable as portable
    from pietto._project import project_sql_emission_rows as rows

    body = f"table result:\n    from words\n    select:\n        id\n        {item}\n"
    with monkeypatch.context() as patch:
        patch.setattr(rows, "MYSQL_PACKET_FLOOR_CHARACTERS", 1 << 20)
        _, outcome = lpad_now_world(tmp_path, "words", "mysql", body, policy)
        artifact = outcome.artifact
        assert artifact is not None, outcome.blockers
        observed = portable.export_emission_observation(artifact, artifact.request)
        loaded = _loaded(artifact)
    _assert_every_reader_refuses(artifact, observed, loaded, "lpad realization")


def _reencoded(payload, change):
    """``payload`` with ``change`` applied to every record, canonically
    encoded again: a forger's bundle, which needs its own pin."""
    description = wire.decode(payload)
    members = tuple(
        (name, tuple(map(change, records))) for name, records in description.members
    )
    return wire.encode(
        wire.Description(
            description.compatibility, description.producer, description.query, members
        )
    )


def _with_field(record, name, value):
    values = list(record.values)
    values[wire.FIELDS[record.address.kind].index(name)] = value
    return wire.Record(record.address, tuple(values))


def _renumbered(doc):
    """An observation document edited by hand, put back in the canonical
    first-visit preorder from its root: unreached records dropped and every
    local reference renumbered."""
    kinds = {record["ref"][0] for record in doc["records"]}
    fields = {tuple(record["ref"]): record["fields"] for record in doc["records"]}

    def local(value):
        return (
            type(value) is list
            and len(value) == 2
            and type(value[0]) is str
            and value[0] in kinds
            and type(value[1]) is int
        )

    def children(value):
        if local(value):
            return [tuple(value)]
        if type(value) is dict:
            value = list(value.values())
        if type(value) is not list:
            return []
        return [ref for item in value for ref in children(item)]

    new, counts, order, pending = {}, {}, [], [tuple(doc["root"])]
    while pending:
        ref = pending.pop()
        if ref not in new:
            new[ref] = [ref[0], counts.get(ref[0], 0)]
            counts[ref[0]] = new[ref][1] + 1
            order.append(ref)
            pending.extend(reversed(children(fields[ref])))

    def renamed(value):
        if local(value):
            return new[tuple(value)]
        if type(value) is list:
            return [renamed(item) for item in value]
        if type(value) is dict:
            return {key: renamed(item) for key, item in value.items()}
        return value

    records = [{"ref": new[ref], "fields": renamed(fields[ref])} for ref in order]
    return json.dumps(
        {"format": doc["format"], "root": new[tuple(doc["root"])], "records": records},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()


def _assert_bundle_loads_or_refused(built, payload, refused):
    """Compiled replay, its template and the public loader under ``payload``'s
    own pin: all accept it, or all refuse it as outside the physical domain
    (load_bundle as PIE-R1004)."""
    import pietto.execution as execution
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    pin = wire.content_pin(payload)
    loaded = load_compiled(
        payload,
        expected_pin=pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )

    def public():
        return execution.load_bundle(
            payload,
            expected_pin=pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility[-1],
        )

    if not refused:
        emit_compiled(loaded, ())
        prepare_compiled_template(loaded)
        public()
        return
    for replay in (
        lambda: emit_compiled(loaded, ()),
        lambda: prepare_compiled_template(loaded),
    ):
        with pytest.raises(wire.CompiledError, match="^COMPILED_PHYSICAL_DOMAIN$"):
            replay()
    with pytest.raises(execution.RequestRejected) as rejected:
        public()
    assert (rejected.value.code, rejected.value.detail) == (
        "PIE-R1004",
        "COMPILED_PHYSICAL_DOMAIN",
    )


def _observation(artifact):
    """The parsed canonical observation document of a native artifact."""
    import _pietto_sql_emission_portable as portable

    assert artifact is not None
    export = portable.export_emission_observation(artifact, artifact.request)
    assert export.canonical_bytes is not None
    return json.loads(export.canonical_bytes)


def _selected(*items):
    return "table result:\n    from rows\n    select:\n        id\n" + "".join(
        f"        {item}\n" for item in items
    )


# A native in-cell body, the operator of a second value of the same row and
# the operator of the cell's operation (or capture read) that the forgery
# makes that value read as its first operand; with one operator twice, the
# forgery makes every reference to the row's last such operation name its
# first instead.
_REUSED = {
    "lpad_twice_in_its_row": (
        "rows",
        _selected('p = lpad(text, 5, "0")', 'q = lpad(text, 5, "0")'),
        ("scalar_call", "lpad"),
        ("scalar_call", "lpad"),
    ),
    "lpad_in_a_comparison": (
        "rows",
        _selected('p = lpad(text, 5, "0")', 'b = text == "x"'),
        ("comparison", "=="),
        ("scalar_call", "lpad"),
    ),
    "lpad_in_lower": (
        "rows",
        _selected('p = lpad(text, 5, "0")', "q = lower(text)"),
        ("scalar_call", "lower"),
        ("scalar_call", "lpad"),
    ),
    "lpad_in_len": (
        "rows",
        _selected('p = lpad(text, 5, "0")', "n = len(text)"),
        ("scalar_call", "len"),
        ("scalar_call", "lpad"),
    ),
    "now_in_a_comparison": (
        "temporal",
        _selected("t = now()", "b = ts > ts"),
        ("comparison", ">"),
        ("scalar_call", "now"),
    ),
    "now_in_hour": (
        "temporal",
        _selected("t = now()", "h = hour(ts)"),
        ("scalar_call", "hour"),
        ("scalar_call", "now"),
    ),
    "now_of_date_of_in_hour": (
        "temporal",
        _selected("d = date_of(now())", "h = hour(ts)"),
        ("scalar_call", "hour"),
        ("scalar_call", "now"),
    ),
    "date_of_in_a_comparison": (
        "temporal",
        _selected("x = date_of(now())", "b = d == d"),
        ("comparison", "=="),
        ("scalar_call", "date_of"),
    ),
    "capture_read_in_a_comparison": (
        "pair",
        LPAD_NOW_PAIRS["s12_capture_context"] + '        b = label == "x"\n',
        ("comparison", "=="),
        ("scalar", "scalar"),
    ),
}


@pytest.mark.parametrize("shape", sorted(_REUSED))
def test_mysql_cell_operations_reused_in_their_row_fail_compiled_and_pure_readers(
    tmp_path, shape
):
    """A forger who rewrites a native in-cell bundle or observation so that
    another value of the same row reads the cell's lpad, now(), date_of or
    capture read as an operand, or is that same operation (records may share an
    operation; a SELECT item never does), gets compiled replay, its
    template, load_bundle and the pure boundary to refuse it; the untouched
    bytes pass. The plan readers never see such a graph: the same nesting
    written in source is in LPAD_NOW_REFUSALS."""
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_compiled_build import build_compiled

    world, body, victim, shared = _REUSED[shape]
    merged = victim == shared
    _, outcome = lpad_now_world(tmp_path, world, "mysql", body)
    artifact = outcome.artifact
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(artifact)
    operations = [
        record
        for record in wire.decode(built.payload).records
        if record.address.kind == "operation"
    ]
    target = [r.address for r in operations if r.get("operator") == shared]
    target = target[0 if merged else -1]
    reader = [r.address for r in operations if r.get("operator") == victim][-1]

    def renamed(value: Any) -> Any:
        if type(value) is tuple:
            return tuple(map(renamed, value))
        return target if value == reader else value

    def reuse(record):
        if merged and record.address != reader:
            return wire.Record(record.address, renamed(record.values))
        if merged or record.address != reader:
            return record
        return _with_field(record, "operands", (target, *record.get("operands")[1:]))

    _assert_bundle_loads_or_refused(built, built.payload, False)
    _assert_bundle_loads_or_refused(built, _reencoded(built.payload, reuse), True)

    def operator(record):
        kind, fields = record["ref"][0], record["fields"]
        if kind == "sql_block_read":
            return ("scalar", fields["kind"])
        return (fields["kind"], fields["operator"]) if kind == "sql_operation" else None

    doc = _observation(artifact)
    assert pure.parse_emission_observation(_renumbered(doc)).status is pure.Status.OK
    found = [r["ref"] for r in doc["records"] if operator(r) == shared]
    found = found[0 if merged else -1]
    (*_, last) = (r for r in doc["records"] if operator(r) == victim)

    def named(value):
        if value == last["ref"]:
            return found
        if type(value) is dict:
            return {key: named(item) for key, item in value.items()}
        return list(map(named, value)) if type(value) is list else value

    if merged:
        doc["records"] = [named(r) for r in doc["records"] if r is not last]
    else:
        last["fields"]["operands"][0] = found
    refused = pure.parse_emission_observation(_renumbered(doc))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "mysql scalar cell",
    )


def test_a_mysql_cell_column_shared_with_a_lower_body_fails_the_pure_boundary(
    tmp_path,
):
    """An observation forged so that a let body lists the final body's
    in-cell lpad column at the same position (a document may share a
    column; a SELECT item never is a let's) is refused at its cell."""
    import _pietto_sql_emission_pure_boundary as pure

    _, outcome = lpad_now_world(
        tmp_path, "words", "mysql", LPAD_NOW_PAIRS["s12_context"]
    )
    artifact = outcome.artifact
    assert outcome.status == "VERIFIED", outcome.blockers
    doc = _observation(artifact)
    fields = {tuple(r["ref"]): r["fields"] for r in doc["records"]}
    bodies = [found for ref, found in fields.items() if ref[0] == "row_body"]
    final = next(body for body in bodies if body["final"] is True)
    below = next(body for body in bodies if body["final"] is not True)
    assert below["block_kind"] == "let"
    position, column = next(
        (position, column)
        for position, column in enumerate(final["columns"])
        if column[0] == "row_value_column"
        and fields[tuple(fields[tuple(column)]["value"])].get("operator") == "lpad"
    )
    below["columns"][position] = column
    refused = pure.parse_emission_observation(_renumbered(doc))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "mysql scalar cell",
    )


def test_a_negative_mysql_lpad_width_literal_fails_compiled_and_pure_readers(
    tmp_path,
):
    """Source cannot write a negative Int literal (`-1` is a sign operation,
    outside every cell), but a forger can write -1 into the width literal of
    an in-cell bundle or observation: compiled replay, its template,
    load_bundle and the pure boundary refuse it, as every reader keeps a
    MySQL width from 0 to 256."""
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_compiled_build import build_compiled

    _, outcome = lpad_now_world(
        tmp_path, "rows", "mysql", _selected('p = lpad(text, 256, "0")')
    )
    artifact = outcome.artifact
    assert outcome.status == "VERIFIED", outcome.blockers
    built = build_compiled(artifact)

    def negative(record):
        if record.address.kind == "literal" and record.get("value") == wire.Scalar(
            "Int", 256
        ):
            return _with_field(record, "value", wire.Scalar("Int", -1))
        return record

    payload = _reencoded(built.payload, negative)
    assert payload != built.payload
    _assert_bundle_loads_or_refused(built, payload, True)
    doc = _observation(artifact)
    (literal,) = (
        r["fields"]["value"]
        for r in doc["records"]
        if r["ref"][0] == "sql_literal" and r["fields"]["value"]["tag"] == "Int"
    )
    literal["value"] = "-1"
    refused = pure.parse_emission_observation(_renumbered(doc))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "lpad realization",
    )


def _stage_labelled(doc, labels):
    """``doc`` with each row body's block kind renamed by ``labels``."""
    edited = json.loads(json.dumps(doc))
    for record in edited["records"]:
        fields = record["fields"]
        if record["ref"][0] == "row_body" and fields["block_kind"] in labels:
            fields["block_kind"] = labels[fields["block_kind"]]
    return _renumbered(edited)


@pytest.mark.parametrize("shape", ("qualify_lpad_field", "qualify_now"))
def test_a_forged_mysql_qualify_relabelled_where_fails_every_reader(
    tmp_path, monkeypatch, shape
):
    """A QUALIFY body forged past the cell law and then relabelled to read as
    a WHERE fails every reader: the plan readers refuse the artifact;
    load_compiled and load_bundle refuse the bundle whose qualify row says
    where (COMPILED_ROW_SHAPE), as only a window feeds a qualify, so no
    compiled replay or template reads it; and the pure boundary refuses the
    observation whose qualify body says where, alone (out of order) or with
    its window body saying let (in order by label, not by structure).
    Nulling the window body's stage field too is refused as a body whose
    window columns name no window stage, and the cell law alone still sees
    those columns as a window under the WHERE."""
    import pietto.execution as execution
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled

    derive, docs = pure._mysql_scalar_cells, []
    monkeypatch.setattr(
        pure, "_mysql_scalar_cells", lambda d: docs.append(d) or derive(d)
    )
    world, policy, body = LPAD_NOW_REFUSALS[shape]
    with monkeypatch.context() as patch:
        patch.setattr(rows, "mysql_scalar_cell", _in_a_cell(rows.mysql_scalar_cell))
        _, outcome = lpad_now_world(tmp_path, world, "mysql", body, policy)
        artifact = outcome.artifact
        assert artifact is not None, outcome.blockers
        observed = portable.export_emission_observation(artifact, artifact.request)
        built = build_compiled(artifact)
        loaded = _loaded(artifact)
    _assert_every_reader_refuses(artifact, observed, loaded, "mysql scalar cell")

    def where(record):
        if record.address.kind == "row" and record.get("stage") == "qualify":
            return _with_field(record, "stage", "where")
        return record

    payload = _reencoded(built.payload, where)
    assert payload != built.payload
    with pytest.raises(wire.CompiledError, match="^COMPILED_ROW_SHAPE$"):
        load_compiled(
            payload,
            expected_pin=wire.content_pin(payload),
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    with pytest.raises(execution.RequestRejected) as rejected:
        execution.load_bundle(
            payload,
            expected_pin=wire.content_pin(payload),
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility[-1],
        )
    assert rejected.value.detail == "COMPILED_ROW_SHAPE"
    assert observed.canonical_bytes is not None
    doc = json.loads(observed.canonical_bytes)
    relabelled = {"qualify": "where", "window": "let"}
    for labels in ({"qualify": "where"}, relabelled):
        refused = pure.parse_emission_observation(_stage_labelled(doc, labels))
        assert (refused.status, refused.detail) == (
            pure.Status.INVALID_RELATION,
            "mysql scalar cell",
        )
    labelled = docs[-1]
    (window,) = (
        ref for ref in labelled.all("row_body") if labelled[ref]["window"] is not None
    )
    for record in doc["records"]:
        if record["ref"][0] == "row_body" and record["fields"]["window"] is not None:
            record["fields"]["window"] = None
    refused = pure.parse_emission_observation(_stage_labelled(doc, relabelled))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "stage columns",
    )
    nulled = pure.Record(window, {**labelled[window], "window": None})
    assert derive(pure._Doc({**labelled.records, window: nulled})) == {}


def test_mysql_cell_stages_come_from_each_body_not_its_label(tmp_path, monkeypatch):
    """The pure boundary takes a row body's stage from what it renders (a
    predicate makes a where, window columns a window, neither a let or the
    projection, aggregate columns none) and needs its label to agree: a
    native in-cell observation whose WHERE body says let, or whose lets say
    where, is refused at its cell, and a final projection that filters or
    windows, or a capturing let's projection that filters, opens no cell.
    The pure boundary and compiled replay each take one WHERE at most, over
    the lets: a second WHERE, or a WHERE under a let, opens no cell."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows

    derive, docs = pure._mysql_scalar_cells, []

    def spied(doc):
        docs.append(doc)
        return derive(doc)

    monkeypatch.setattr(pure, "_mysql_scalar_cells", spied)
    bundles = {}
    for world, form in (("words", "s12_context"), ("pair", "s12_capture_context")):
        _, outcome = lpad_now_world(
            tmp_path / form, world, "mysql", LPAD_NOW_PAIRS[form]
        )
        artifact = outcome.artifact
        assert outcome.status == "VERIFIED" and artifact is not None, outcome.blockers
        export = portable.export_emission_observation(artifact, artifact.request)
        assert export.canonical_bytes is not None
        assert pure.parse_emission_observation(export.canonical_bytes).status is (
            pure.Status.OK
        )
        if form == "s12_context":
            bundles[form] = _loaded(artifact)
            doc = json.loads(export.canonical_bytes)
            for labels in ({"where": "let"}, {"let": "where"}):
                labelled = _stage_labelled(doc, labels)
                refused = pure.parse_emission_observation(labelled)
                assert (refused.status, refused.detail) == (
                    pure.Status.INVALID_RELATION,
                    "mysql scalar cell",
                )
    context, capture = docs[0], docs[-1]

    def body(doc, **found):
        (ref,) = (
            ref
            for ref in doc.all("row_body")
            if all(doc[ref][name] == value for name, value in found.items())
        )
        return ref

    def edited(doc, ref, **changes):
        record = pure.Record(ref, {**doc[ref], **changes})
        return pure._Doc({**doc.records, ref: record})

    def stage(*kinds, predicate=None):
        columns = tuple(pure.Ref(kind, 0) for kind in kinds)
        return pure._mysql_stage({"columns": columns, "predicate": predicate})

    final = body(context, final=True)
    filters = body(context, block_kind="where")
    where = context[filters]["predicate"]
    below = context[context[filters]["scan"]]["body"]
    window = next(
        column
        for column in context[body(context, block_kind="window")]["columns"]
        if column.kind == "window_column"
    )
    producer = body(capture, final=False, block_kind="projection")
    filtered = capture[body(capture, block_kind="where")]["predicate"]
    assert derive(context) and derive(capture)
    assert context[below]["block_kind"] == "let"
    assert [stage("row_value_column"), stage("window_column")] == ["let", "window"]
    assert stage("row_value_column", predicate=where) == "where"
    assert stage("window_column", predicate=where) is None
    assert stage("aggregate_key_column") is stage("aggregate_value_column") is None
    assert derive(edited(context, final, predicate=where)) == {}
    columns = (*context[final]["columns"], window)
    assert derive(edited(context, final, columns=columns)) == {}
    assert derive(edited(capture, producer, predicate=filtered)) == {}
    twice = edited(context, below, predicate=where, block_kind="where")
    assert derive(twice) == {}
    unfiltered = edited(context, filters, predicate=None, block_kind="let")
    assert derive(edited(unfiltered, below, predicate=where, block_kind="where")) == {}

    loaded = bundles["s12_context"]
    records = loaded.records
    entry = records[loaded.description.query]
    (where_row,) = (
        record
        for record in records.values()
        if record.address.kind == "row" and record.get("stage") == "where"
    )
    below_row = records[where_row.get("input")]
    assert rows.mysql_compiled_scalar_cells(records, entry)
    assert below_row.get("stage") == "let"

    def staged(*changes):
        changed = dict(records)
        for record, label in changes:
            changed[record.address] = _with_field(record, "stage", label)
        return changed

    for changes in (
        ((below_row, "where"),),
        ((where_row, "let"), (below_row, "where")),
    ):
        assert rows.mysql_compiled_scalar_cells(staged(*changes), entry) == {}


def _token(kind, role, subject, text):
    return {"kind": kind, "role": role, "subject": subject, "start": 0, "end": 0}, text


def _retokened(doc, edit):
    """``doc`` with its token list edited, renumbered: ``edit`` takes and
    returns (event fields, text) pairs; the SQL and the offsets follow, each
    subject keeps its origins and the optional expression ranges go."""
    edited = json.loads(json.dumps(doc))
    fields = {tuple(r["ref"]): r["fields"] for r in edited["records"]}
    (rendered,) = (r["fields"] for r in edited["records"] if r["ref"][0] == "rendered")
    sql = rendered["sql"].encode()
    tokens = [
        (event, sql[event["start"] : event["end"]].decode())
        for event in (fields[tuple(ref)] for ref in rendered["events"])
    ]
    origins = {json.dumps(event["subject"]): event["origins"] for event, _ in tokens}
    edited["records"] = [r for r in edited["records"] if r["ref"][0] != "event"]
    sql, refs = b"", []
    for n, (event, text) in enumerate(edit(tokens)):
        start, sql = len(sql), sql + text.encode()
        event = {**event, "start": start, "end": len(sql)}
        event["origins"] = origins.get(json.dumps(event["subject"]), [])
        refs.append(["event", n])
        edited["records"].append({"ref": refs[-1], "fields": event})
    rendered.update(sql=sql.decode(), events=refs, expression_ranges=[])
    return _renumbered(edited)


def _wrapped(tokens, scan, alias, opener):
    """``tokens`` as a scalar subquery of one scan, (SELECT ... FROM scan AS
    alias), spelled with roles that need no block read record."""
    (as_, _), (scope, _) = scan[3:]
    return [
        (opener, "("),
        ({**opener, "role": "membership_select"}, "SELECT "),
        *tokens,
        ({**opener, "role": "membership_from"}, " FROM "),
        *scan[:3],
        ({**as_, "role": "exists_alias"}, " AS "),
        (scope, alias),
        ({**opener, "role": "binary_close"}, ")"),
    ]


# Record forgeries, each with the SQL forgery x_reads_the_id it agrees with.
_RECORD_FORGERIES = (
    "x_reads_the_id_record",
    "x_reads_the_id_retyped",
    "x_claims_its_text_field",
)


def _forged_cell_sql(doc, forgery):
    """The native s12_context observation ``doc``, whose final query reads
    p4 (a window over a WHERE over lets), with one forgery of its SQL that
    leaves the records the cell law reads, or one of _RECORD_FORGERIES."""
    forged = json.loads(json.dumps(doc))
    fields = {tuple(r["ref"]): r["fields"] for r in forged["records"]}
    final = next(f for k, f in fields.items() if k[0] == "row_body" and f["final"])
    ident = fields[tuple(fields[tuple(final["columns"][0])]["value"])]
    lpad = next(
        f
        for k, f in fields.items()
        if k[0] == "sql_operation" and f["operator"] == "lpad"
    )
    x = fields[tuple(lpad["operands"][0])]  # the text operand of the item p
    if forgery == "width_300":
        (literal,) = (
            f
            for k, f in fields.items()
            if k[0] == "sql_literal" and f["value"] == {"tag": "Int", "value": "2"}
        )
        literal["value"]["value"] = "300"  # WHERE id > 2 becomes id > 300
    elif forgery == "x_reads_the_id_record":
        x["column"] = ident["column"]
    elif forgery in _RECORD_FORGERIES:
        column = (
            {**fields[tuple(ident["column"])], "realization": x["realization"]}
            if forgery == "x_reads_the_id_retyped"
            else {**fields[tuple(x["column"])], "name": "c0"}
        )
        forged["records"].append({"ref": ["stage_column", 1 << 20], "fields": column})
        x["column"] = ["stage_column", 1 << 20]

    def at(tokens, role, text=None, after=0):
        return next(
            i
            for i, (event, spelled) in enumerate(tokens)
            if i >= after and event["role"] == role and text in (None, spelled)
        )

    def edit(tokens):
        s = max(i for i, (event, _) in enumerate(tokens) if event["role"] == "select")
        item, select = tokens[s + 1 : s + 4], tokens[s][0]  # `t5`.`c0` AS `id`
        now = at(tokens, "scalar_call_open", "UTC_TIMESTAMP(6")
        a = at(tokens, "scalar_call_open", "CASE WHEN CHAR_LENGTH(", s)
        b = at(tokens, "alias", after=a)  # the item p is tokens[a:b]
        scan = tokens[at(tokens, "namespace") :][:5]
        opener = {**select, "role": "binary_open"}
        clauses = {
            "group_by": (" GROUP BY ", "grouping"),
            "order_by": (" ORDER BY ", "order"),
            "where": (" WHERE ", "value"),
        }
        if forgery in clauses:
            text, prefix = clauses[forgery]
            roles = (prefix + "_scope", prefix + "_qualifier", prefix + "_column")
            clause = [
                ({**e, "role": r}, t) for (e, t), r in zip(item, roles, strict=True)
            ]
            return [*tokens, ({**select, "role": forgery}, text), *clause]
        if forgery == "distinct":
            distinct = ({**select, "role": "distinct"}, "DISTINCT ")
            return [*tokens[: s + 1], distinct, *tokens[s + 1 :]]
        if forgery == "subquery":
            subquery = _wrapped(item, scan, item[0][1], opener)
            return [*tokens[: s + 1], *subquery, *tokens[s + 4 :]]
        if forgery == "window_subquery":
            w = at(tokens, "window_order_scope")
            subquery = _wrapped(tokens[w : w + 3], scan, tokens[w][1], opener)
            return [*tokens[:w], *subquery, *tokens[w + 3 :]]
        if forgery == "window_where":
            w = at(tokens, "window_order_scope")
            roles = ("value_scope", "value_qualifier", "value_column")
            read = [
                ({**e, "role": r}, t)
                for (e, t), r in zip(tokens[w : w + 3], roles, strict=True)
            ]
            end = at(tokens, "with_body") - 1  # p4's cte_body_close
            where = ({**select, "role": "where"}, " WHERE ")
            return [*tokens[:end], where, *read, *tokens[end:]]
        if forgery == "window_clause":
            # WINDOW `t5` AS () after the query, named by a spelled scope.
            name = ({**item[0][0], "role": "window_order_scope"}, item[0][1])
            spelled = [
                ({**select, "role": r}, t)
                for r, t in (
                    ("window_definition_as", " AS "),
                    ("window_spec_open", "("),
                    ("window_spec_close", ")"),
                )
            ]
            clause = ({**select, "role": "window_clause"}, " WINDOW ")
            return [*tokens, clause, name, *spelled]
        if forgery == "cycle":
            uses = [
                i for i, (e, _) in enumerate(tokens) if e["role"] == "stage_reference"
            ]
            tokens[uses[0]] = tokens[uses[2]]  # p1 reads p2, which reads p1
            return tokens
        if forgery in ("now_compared", "lpad_compared"):
            compare = tokens[at(tokens, "comparison_operator")]  # WHERE id > 2
            first, last = (now, now + 2) if forgery == "now_compared" else (a, b)
            return [
                *tokens[:first],
                ({**compare[0], "role": "comparison_open"}, "("),
                *tokens[first:last],
                compare,
                *item,
                ({**compare[0], "role": "comparison_close"}, ")"),
                *tokens[last:],
            ]
        if forgery == "comma":
            comma = ({**tokens[now][0], "role": "scalar_call_separator"}, ", ")
            return [*tokens[: s + 4], comma, *item, *tokens[s + 4 :]]
        if forgery == "now_twice":
            return [*tokens[: s + 4], *tokens[now : now + 2], *tokens[s + 4 :]]
        if forgery == "items_swapped":
            return [
                *tokens[: s + 1],
                *tokens[a:b],
                *tokens[s + 4 : a],
                *item,
                *tokens[b:],
            ]
        if forgery == "width_300":
            where = at(tokens, "Int", after=at(tokens, "where"))
            return [
                (tokens[where][0], "300")
                if i == where or (a < i < b and token[0]["role"] == "Int")
                else token
                for i, token in enumerate(tokens)
            ]
        assert forgery == "x_reads_the_id" or forgery in _RECORD_FORGERIES
        return [
            item[2] if a < i < b and token[0]["role"] == "value_column" else token
            for i, token in enumerate(tokens)
        ]

    return _retokened(forged, edit)


@pytest.mark.parametrize(
    "forgery",
    (
        "group_by",
        "order_by",
        "where",
        "distinct",
        "subquery",
        "window_subquery",
        "window_where",
        "window_clause",
        "cycle",
        "comma",
        "now_twice",
        "now_compared",
        "lpad_compared",
        "items_swapped",
        "width_300",
        "x_reads_the_id",
        *_RECORD_FORGERIES,
    ),
)
def test_mysql_cells_are_read_from_the_rendered_sql(tmp_path, forgery):
    """The pure boundary reads each MySQL lpad and now() cell from the SQL
    tokens themselves, not from the records the cell law reads, which no
    token check ties to the SQL. A native in-cell observation whose SQL gains
    a GROUP BY, ORDER BY or WHERE in its final query, a DISTINCT, a scalar
    subquery in an item or in a window's ORDER BY, a WHERE in its window
    body (a second WHERE), a WINDOW clause in its final query named by a
    spelled scope, a cycle of lets, a second select item behind a
    comma or a second now(), whose now() or lpad becomes one side of a
    comparison or trades places with another item, whose lpad width reads
    another literal (300, rewritten), or whose lpad reads the Int id column
    instead of its text is refused at its cell, its records unchanged; so are
    the reads of the id column whose operand record names the id column (a
    Text reference to an Int column), names it retyped as Text, or names its
    own text field under the id column's name. The untouched tokens, without
    their optional ranges, pass."""
    import _pietto_sql_emission_pure_boundary as pure

    _, outcome = lpad_now_world(
        tmp_path, "words", "mysql", LPAD_NOW_PAIRS["s12_context"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    doc = _observation(outcome.artifact)
    native = pure.parse_emission_observation(_retokened(doc, lambda tokens: tokens))
    assert native.status is pure.Status.OK
    refused = pure.parse_emission_observation(_forged_cell_sql(doc, forgery))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "mysql scalar cell",
    )


def _forged_capture_sql(tokens, forgery):
    """The tokens of the native s12_capture_context observation, whose item
    m is (SELECT e0.c1 FROM (<let> FROM (<where>) AS t1) AS e0), with one
    forgery."""

    def at(role):
        return next(i for i, (e, _) in enumerate(tokens) if e["role"] == role)

    def renamed(i, role, text=None):
        return ({**tokens[i][0], "role": role}, tokens[i][1] if text is None else text)

    read = at("scalar_open")
    let = read + 6  # the let's inline_open; its first value is let + 2 .. 4
    close = at("scalar_close") - 3  # the let's inline_close
    where, inner = at("where"), at("inline_close")  # the WHERE body's
    if forgery == "head":
        tokens[read + 1] = renamed(read + 1, "membership_select")
    elif forgery == "tail":
        tokens[close + 1] = renamed(close + 1, "exists_alias")
    elif forgery == "closed_early":
        early = [renamed(read, "binary_close", ")"), renamed(read, "binary_open")]
        tokens[let + 5 : let + 5] = early
    elif forgery == "let_filters":
        tokens[close:close] = [tokens[where], *tokens[let + 2 : let + 5]]
    elif forgery == "source_unfiltered":
        captured = tokens[at("capture_scope") :][:3]
        tokens[where:inner] = []
        tokens[let + 8 : let + 11] = captured  # the let's c1 reads s1
    else:
        assert forgery == "derived_table"
        scan = len(tokens) - 5  # FROM <namespace>.<relation> AS s1
        alias = tokens[scan + 3]
        tokens[scan:] = [
            *tokens[let : close + 1],
            alias,
            renamed(scan + 4, "stage_scope"),
        ]
        tokens[read : at("scalar_close") + 1] = tokens[1:4]  # m reads id
    return tokens


@pytest.mark.parametrize(
    "forgery",
    (
        "head",
        "tail",
        "closed_early",
        "let_filters",
        "source_unfiltered",
        "derived_table",
    ),
)
def test_a_mysql_capture_read_is_read_from_the_rendered_sql(tmp_path, forgery):
    """A native observation with a capture read beside its cells is refused
    at its cells, its records unchanged, when the read's SQL leaves the
    grammar: its SELECT or AS spelled by another role, an item that closes
    the let's parenthesis early, a WHERE in the capturing let, a source
    body that no longer filters (its let reads the captured field instead),
    or the let moved from the read into the query's FROM."""
    import _pietto_sql_emission_pure_boundary as pure

    _, outcome = lpad_now_world(
        tmp_path, "pair", "mysql", LPAD_NOW_PAIRS["s12_capture_context"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    doc = _observation(outcome.artifact)
    forged = _retokened(doc, lambda tokens: _forged_capture_sql(tokens, forgery))
    refused = pure.parse_emission_observation(forged)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "mysql scalar cell",
    )


@pytest.mark.parametrize("forgery", ("order_by", "subquery"))
def test_a_mysql_window_clause_beside_a_cell_is_read_from_the_rendered_sql(
    tmp_path, forgery
):
    """A native in-cell observation whose WINDOW clause is followed by an
    ORDER BY, or whose first definition orders by a scalar subquery, is
    refused at its cell, its records unchanged; the untouched tokens, with
    two definitions, pass."""
    import _pietto_sql_emission_pure_boundary as pure

    _, outcome = lpad_now_world(
        tmp_path,
        "words",
        "mysql",
        "table result:\n    from words\n    let w = window(order by id)\n"
        "    let v = window(partition by text order by id desc)\n"
        "    select:\n        id\n        r = row_number() window w\n"
        "        k = rank() window v\n"
        '        p = lpad(text, 5, "0")\n',
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    doc = _observation(outcome.artifact)

    def edit(tokens):
        roles = [event["role"] for event, _ in tokens]
        w = roles.index("window_order_scope")  # in the definition only
        read = tokens[w : w + 3]
        if forgery == "order_by":
            close = roles.index("window_spec_close") + 1
            order = ({**tokens[close - 1][0], "role": "window_order"}, "ORDER BY ")
            return [*tokens[:close], order, *read, *tokens[close:]]
        scan = tokens[roles.index("namespace") :][:5]
        select = tokens[len(roles) - 1 - roles[::-1].index("select")][0]
        subquery = _wrapped(read, scan, read[0][1], {**select, "role": "binary_open"})
        return [*tokens[:w], *subquery, *tokens[w + 3 :]]

    native = pure.parse_emission_observation(_retokened(doc, lambda tokens: tokens))
    assert native.status is pure.Status.OK
    refused = pure.parse_emission_observation(_retokened(doc, edit))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "mysql scalar cell",
    )


def test_a_mysql_lpad_fill_read_from_another_literal_fails_the_pure_boundary(
    tmp_path,
):
    """A native in-cell observation whose first lpad's fill token reads the
    six-character literal of the second lpad, records unchanged, renders a
    fill outside the cell and is refused at its cell."""
    import _pietto_sql_emission_pure_boundary as pure

    _, outcome = lpad_now_world(
        tmp_path, "words", "mysql", LPAD_NOW_PAIRS["s12_lpad_literal"]
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    doc = _observation(outcome.artifact)

    def edit(tokens):
        # lpad("ab", 5, "雪") renders ab 5 ab ab 5 雪, then "abcdef" comes.
        literals = [
            i for i, (event, _) in enumerate(tokens) if event["kind"] == "literal"
        ]
        fill, other = literals[5], literals[6]
        assert tokens[other][1] == "X'616263646566'"
        tokens[fill] = (
            {**tokens[fill][0], "subject": tokens[other][0]["subject"]},
            tokens[other][1],
        )
        return tokens

    refused = pure.parse_emission_observation(_retokened(doc, edit))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "mysql scalar cell",
    )


@pytest.mark.parametrize(
    "argument",
    (
        "1) OVER ()) SELECT 1 AS `id` -- ",
        "1) OVER () LIMIT 1), `zz` AS (SELECT NTILE(1",
    ),
)
def test_a_mysql_window_argument_literal_beside_a_cell_is_an_integer_or_null(
    tmp_path, argument
):
    """On MySQL no record bounds the text of a window argument literal. A
    native in-cell observation whose ROW_NUMBER() becomes NTILE with a record
    and token argument that closes the call, then comments out the rest of
    the statement or limits the window's body, is refused at its cell; the
    arguments 1 and NULL pass."""
    import _pietto_sql_emission_pure_boundary as pure

    source = LPAD_NOW_PAIRS["s12_context"]
    _, outcome = lpad_now_world(tmp_path, "words", "mysql", source)
    assert outcome.status == "VERIFIED", outcome.blockers
    doc = _observation(outcome.artifact)

    def ntile(argument):
        forged = json.loads(json.dumps(doc))
        (window,) = (r for r in forged["records"] if r["ref"][0] == "window_column")
        window["fields"]["function"] = "ntile"
        window["fields"]["arguments"] = [["window_argument", 1 << 20]]
        literal = {"position": 0, "role": "bucket", "read": None, "literal": argument}
        forged["records"].append(
            {"ref": ["window_argument", 1 << 20], "fields": literal}
        )

        def edit(tokens):
            w = next(i for i, (e, _) in enumerate(tokens) if e["role"] == "window_open")
            subject = tokens[w][0]["subject"]
            ntile = (tokens[w][0], "NTILE(")
            argument_token = _token(
                "literal", "window_argument_literal", subject, argument
            )
            return [*tokens[:w], ntile, argument_token, *tokens[w + 1 :]]

        return pure.parse_emission_observation(_retokened(forged, edit))

    assert ntile("1").status is ntile("NULL").status is pure.Status.OK
    refused = ntile(argument)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "mysql scalar cell",
    )


@pytest.mark.parametrize(
    "form",
    (
        "s12_lpad_field",
        "s12_lpad_literal",
        "s12_now",
        "s12_context",
        "s12_capture_context",
    ),
)
def test_mysql_lpad_and_now_cells_agree_across_readers(tmp_path, monkeypatch, form):
    """Emission (from the plan), compiled replay (from the records) and the
    pure boundary (from the document) derive the same open cells."""
    import _pietto_sql_emission as probe
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows

    law, derive = rows.mysql_scalar_cell, pure._mysql_scalar_cells
    emitted, observed = {}, []

    def recorded(plan, expression, values):
        cell = law(plan, expression, values)
        if cell is not None:
            # Emission realizes a call more than once; count it once.
            emitted[id(expression.expression)] = cell
        return cell

    world = "pair" if form == "s12_capture_context" else "words"
    with monkeypatch.context() as patch:
        patch.setattr(rows, "mysql_scalar_cell", recorded)
        _, outcome = lpad_now_world(
            tmp_path, world, "mysql", probe.LPAD_NOW_PAIRS[form]
        )
    artifact = outcome.artifact
    assert artifact is not None, outcome.blockers
    loaded = _loaded(artifact)
    replayed = rows.mysql_compiled_scalar_cells(
        loaded.records, loaded.records[loaded.description.query]
    )

    def spied(doc):
        found = derive(doc)
        observed.extend(found.values())
        return found

    with monkeypatch.context() as patch:
        patch.setattr(pure, "_mysql_scalar_cells", spied)
        export = portable.export_emission_observation(artifact, artifact.request)
        assert export.canonical_bytes is not None
        assert pure.parse_emission_observation(export.canonical_bytes).status is (
            pure.Status.OK
        )
    assert sorted(emitted.values()) == sorted(replayed.values()) == sorted(observed)
    assert set(emitted.values()) <= rows.MYSQL_SCALAR_CELLS


def test_compiled_replay_counts_the_rendered_parameter_markers(tmp_path, monkeypatch):
    """A PostgreSQL `lpad` whose repeated text operand renders a capture
    read's bind-safe markers, forged past the live parameter law, loads; its
    compiled replay and template refuse it (six markers, two uses). MySQL
    refuses the same forgery earlier, outside the lpad cells."""
    import builtins

    import _pietto_sql_emission as probe
    from pietto._project import project_sql_emission as emission
    from pietto._project import project_sql_emission_inspection as inspection
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project import project_sql_emission_verification as verification
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    body = (
        "table result:\n    let matched:\n        capture lhs\n        from rhs\n"
        '        where rhs.id == lhs.id and rhs.label == "x" and rhs.id > 7\n'
        "        select:\n            id\n            label\n    from lhs\n"
        '    select:\n        p = lpad(scalar matched.label, 4, "雪")\n'
    )
    law = rows.mysql_scalar_cell

    def opened(plan, expression, values):
        cell = law(plan, expression, values)
        return (
            None
            if cell is None
            else ("lpad", "select", ("field", "literal", "literal"))
        )

    for target, refusal in (
        ("postgres", "COMPILED_EMISSION_PARAMETER_INVENTORY"),
        ("mysql", "COMPILED_PHYSICAL_DOMAIN"),
    ):
        item = probe.labelled_join_witness(target, body, policy="bind_safe_literals")
        with monkeypatch.context() as patch:
            patch.setattr(verification, "verify_row_parameters", lambda artifact: True)
            patch.setattr(emission, "_public_document", lambda outcome: {})
            patch.setattr(
                inspection,
                "zip",
                lambda *args, strict=False: builtins.zip(*args),
                raising=False,
            )
            patch.setattr(rows, "mysql_scalar_cell", opened)
            _, outcome = probe.build_case(
                tmp_path / target,
                item["source"],
                item["contract"],
                "bind_safe_literals",
            )
            artifact = outcome.artifact
            assert artifact is not None
            assert (
                sum(event.kind == "parameter" for event in artifact.rendered.events),
                len(artifact.parameter_uses),
            ) == (6, 2)
            loaded = _loaded(artifact)
        values = tuple(value.value for value in artifact.fixed_values)
        for replay in (
            lambda: emit_compiled(loaded, values),
            lambda: prepare_compiled_template(loaded),
        ):
            with pytest.raises(wire.CompiledError, match=f"^{refusal}$"):
                replay()


@pytest.mark.parametrize("shape", sorted(MYSQL_TYPED_OPEN))
def test_mysql_typed_cells_replay_their_sql_from_the_bundle(tmp_path, shape):
    """S09: compiled replay derives the same MySQL typed cells from the
    records alone; the loaded bundle emits the live SQL and native uses, its
    template prepares, and the pure boundary leaves the template outside its
    schema, as it leaves every header parameter."""
    import _pietto_sql_emission_portable as portable
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    _, outcome = typed_case(tmp_path, "mysql", MYSQL_TYPED_OPEN[shape])
    artifact = outcome.artifact
    assert artifact is not None, outcome.blockers
    loaded = _loaded(artifact)
    assert rows.mysql_compiled_typed_cells(
        loaded.records, loaded.records[loaded.description.query]
    )
    replayed = emit_compiled(loaded, tuple(v.value for v in artifact.fixed_values))
    assert replayed.rendered.sql == artifact.rendered.sql
    assert [(u.physical_type, u.server_index) for u in replayed.parameter_uses] == [
        (u.physical_type, u.server_index) for u in artifact.parameter_uses
    ]
    prepare_compiled_template(loaded)
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OUTSIDE_SCHEMA


# The refused bodies that another rule still refuses when the plan law admits
# every MySQL typed read, or that declare a UUID, which has no MySQL carrier:
# no artifact exists to forge.
_TYPED_UNFORGEABLE = frozenset(
    {"in_list", "coalesce", "add_months", "decimal_conflict", "decimal_arithmetic"}
    | {shape for shape in MYSQL_TYPED_REFUSED if shape.startswith("uuid_")}
)


@pytest.mark.parametrize("shape", sorted(MYSQL_TYPED_REFUSED))
def test_forged_mysql_typed_reads_outside_their_cells_fail_every_reader(
    tmp_path, monkeypatch, shape
):
    """An artifact of each refused body, emitted while the plan law admits
    every MySQL typed read, with its observation and compiled bundle, fails
    plain verification and the live template (plan), the pure boundary
    (document) and compiled replay and its template (records) once the law is
    back."""
    import _pietto_sql_emission_portable as portable
    from pietto._project import project_sql_emission_rows as rows

    with monkeypatch.context() as patch:
        patch.setattr(rows, "mysql_typed_cells", lambda plan: True)
        _, outcome = typed_case(tmp_path, "mysql", MYSQL_TYPED_REFUSED[shape])
        artifact = outcome.artifact
        if shape in _TYPED_UNFORGEABLE:
            assert artifact is None and outcome.blockers
            return
        assert artifact is not None, outcome.blockers
        observed = portable.export_emission_observation(artifact, artifact.request)
        loaded = _loaded(artifact)
    _assert_every_reader_refuses(artifact, observed, loaded, None)


@pytest.mark.parametrize(
    "shape", sorted(s for s in MYSQL_TYPED_REFUSED if s.startswith("uuid_"))
)
def test_a_forged_mysql_uuid_parameter_fails_every_reader(tmp_path, monkeypatch, shape):
    """S09 withdrew MySQL's UUID parameter carrier (D77.07). An artifact of
    each former UUID cell, emitted while the carrier is back, with its
    compiled bundle, fails plain verification and the live template (plan)
    and compiled loading and load_bundle (records) once the carrier is gone.
    The pure boundary (document) refuses it as outside its schema even while
    the carrier is back, since it admits no header parameter."""
    import pietto.execution as execution
    from pietto._project import project_sql_emission_parameters as parameters
    import _pietto_sql_emission_portable as portable
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        BindingError,
        prepare_live_template,
    )
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    with monkeypatch.context() as patch:
        patch.setitem(parameters.HEADER_PHYSICAL["mysql"], "UUID", "my_uuid_bytes")
        patch.setitem(parameters.HEADER_SQL_TYPES, "my_uuid_bytes", "BINARY(16)")
        _, outcome = typed_case(tmp_path, "mysql", MYSQL_TYPED_REFUSED[shape])
        artifact = outcome.artifact
        assert artifact is not None, outcome.blockers
        observed = portable.export_emission_observation(artifact, artifact.request)
        built = build_compiled(artifact)
    assert not verify_project_sql_emission(artifact, artifact.request).verified
    with pytest.raises(BindingError, match="^BINDING_ARTIFACT$"):
        prepare_live_template(artifact)
    assert observed.status is portable.ObservationStatus.OUTSIDE_SCHEMA
    with pytest.raises(wire.CompiledError, match="^COMPILED_PARAMETER$"):
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    with pytest.raises(execution.RequestRejected) as rejected:
        execution.load_bundle(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility[-1],
        )
    # Verification refuses the bytes at load (BUNDLE_NOT_ACCEPTED).
    assert (rejected.value.code, rejected.value.detail) == (
        "PIE-R1008",
        "COMPILED_PARAMETER",
    )


def _swapped_comparison(record):
    if (
        record.address.kind == "operation"
        and record.get("operator")[0] == "comparison"
        and record.get("operands")[1].kind == "parameter_read"
    ):
        left, right = record.get("operands")
        return _with_field(record, "operands", (right, left))
    return record


def _claimed(kind, name, value):
    def change(record):
        if record.address.kind == kind:
            return _with_field(record, name, value)
        return record

    return change


@pytest.mark.parametrize(
    "change,detail",
    (
        (_swapped_comparison, "COMPILED_PHYSICAL_DOMAIN"),
        (_claimed("parameter", "tag", "Timestamp"), "COMPILED_PHYSICAL_DOMAIN"),
        (_claimed("native_use", "physical", "my_datetime"), "COMPILED_PLAN_USES"),
    ),
    ids=("parameter_left", "parameter_tag", "native_carrier"),
)
def test_a_tampered_mysql_typed_bundle_fails_replay_and_load_bundle(
    tmp_path, change, detail
):
    """A forger's bundle of `d == day or d == day` whose comparisons read the
    parameter on the left, whose Date parameter claims Timestamp, or whose
    native uses claim the Timestamp carrier, under its own pin, fails
    compiled replay, its template and load_bundle; the untouched bundle
    loads."""
    import pietto.execution as execution
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    _, outcome = typed_case(tmp_path, "mysql", MYSQL_TYPED_OPEN["twice"])
    built = build_compiled(outcome.artifact)
    _assert_bundle_loads_or_refused(built, built.payload, False)
    payload = _reencoded(built.payload, change)
    pin = wire.content_pin(payload)
    loaded = load_compiled(
        payload,
        expected_pin=pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    for replay in (
        lambda: emit_compiled(loaded, ()),
        lambda: prepare_compiled_template(loaded),
    ):
        with pytest.raises(wire.CompiledError, match=f"^{detail}$"):
            replay()
    with pytest.raises(execution.RequestRejected) as rejected:
        execution.load_bundle(
            payload,
            expected_pin=pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility[-1],
        )
    assert (rejected.value.code, rejected.value.detail) == ("PIE-R1004", detail)


class _IndexedExpressions(_CountedExpressions):
    """_CountedExpressions that also count each item read by its index."""

    def __getitem__(self, index):
        self.yielded += 1
        return super().__getitem__(index)


def _typed_chain(k):
    """k comparisons of one Date parameter chained by `and`, and k SELECT
    items reading it."""
    where = " and ".join(["d == day"] * k)
    items = "".join(f"        a{i} = day\n" for i in range(k))
    return (
        f"query result(day: Date):\n    from rows\n    where {where}\n"
        f"    select:\n        id\n{items}"
    )


def test_mysql_typed_cells_are_derived_in_linear_work(tmp_path, monkeypatch):
    """PERF-2 (S09): the plan law reads each plan expression a bounded number
    of times and compiled replay looks each record up a bounded number of
    times, however long the `and` chain above the comparisons; emission and
    its verification ask the plan law as often for 32 reads as for 4."""
    from pietto._project import project_sql_emission_rows as rows

    law, seen = rows.mysql_typed_cells, []

    def counted(plan):
        wrapped = _CountedPlan(plan)
        wrapped.expressions = _IndexedExpressions(plan.expressions)
        found = law(wrapped)
        seen.append((wrapped.expressions.yielded / len(plan.expressions), found))
        return found

    calls, reads, compiled = {}, {}, {}
    for k in (4, 8, 16, 32):
        seen.clear()
        with monkeypatch.context() as patch:
            patch.setattr(rows, "mysql_typed_cells", counted)
            _, outcome = typed_case(tmp_path / f"k{k}", "mysql", _typed_chain(k))
        assert outcome.status == "VERIFIED", outcome.blockers
        assert seen and all(found for _, found in seen)
        calls[k], reads[k] = len(seen), max(ratio for ratio, _ in seen)
        loaded = _loaded(outcome.artifact)
        records = _CountedRecords(loaded.records)
        assert rows.mysql_compiled_typed_cells(
            records, loaded.records[loaded.description.query]
        )
        compiled[k] = records.count / len(loaded.records)
    assert calls[32] == calls[4]
    # Linear work: the share of reads among records grows with k, so the
    # ratio rises toward a constant; a quadratic climb would double it.
    for k in (8, 16, 32):
        assert reads[k] <= min(reads[k // 2] + 0.15, 3)
        assert compiled[k] <= min(compiled[k // 2] + 0.15, 3)
