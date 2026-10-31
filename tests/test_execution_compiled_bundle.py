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

    forged = wire.Description(
        description.compatibility,
        description.producer,
        description.query,
        tuple(
            (member, tuple(change(r) for r in records_))
            for member, records_ in description.members
        ),
    )
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
    for name, argument in (("call", "Positive(lhs)"), ("expanded", expanded)):
        checked, outcome = probe.build_case(
            tmp_path / name,
            header.replace("ARGUMENT", argument),
            json.dumps(contract),
            item["policy"],
        )
        assert checked.verified is concrete
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
    if concrete:
        assert (
            "PIE-B1003",
            "aggregate_argument_not_a_direct_established_field",
        ) in outcomes[0]


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
