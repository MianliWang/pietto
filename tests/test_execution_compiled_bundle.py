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
    result, error = resolved_binary_value_type("/", integer, integer)
    assert result.kind is ValueTypeKind.UNKNOWN and error is None
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


def _parameterized(directory, target, variant):
    """The compiled root of the published v2 conformance query."""
    import _pietto_sql_emission as probe
    from pietto._project.project_compiled_build import build_compiled

    item = probe.fixture(target, "Q_query_parameters", variant)
    _, outcome = probe.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    return build_compiled(outcome.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_parameterized_root_is_a_v2_payload_no_loader_accepts_yet(tmp_path, target):
    from pietto._project.model import CompiledProjectInput
    from pietto._project.project_execution_template import prepare_compiled_template

    built = _parameterized(tmp_path, target, "bind")
    assert json.loads(built.payload)["format"] == wire.PARAMETERIZED_FORMAT
    assert built.compatibility[: len(wire.VERSIONS)] == wire.VERSIONS
    # Transport of v2 roots is not published: the v1 decoder refuses the tag.
    with pytest.raises(wire.CompiledError, match="^COMPILED_FORMAT$"):
        wire.decode(built.payload)
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
