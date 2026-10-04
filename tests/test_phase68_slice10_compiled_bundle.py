"""Compiled data boundaries stay separate from source and live authority."""

import json
import math

import pytest

from pietto._project import project_compiled_schema as wire
from pietto._project.project_compiled_verification import verify_description
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
