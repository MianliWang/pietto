from __future__ import annotations

from pietto._metadata.builder import _field_leaves
from pietto.ir import (
    CastIR,
    ConditionalIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    MembershipIR,
    NullabilityIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
)


_SPAN = SourceSpan(
    path="metadata-reader.pietto", line=1, column=1, end_line=1, end_column=2
)
_OWNER = SymbolId(SymbolNamespace.RELATION, "records")


def _type(name: str) -> TypeRefIR:
    return TypeRefIR(
        symbol=SymbolId(SymbolNamespace.TYPE, name),
        canonical_symbol=SymbolId(SymbolNamespace.TYPE, name),
        declared_name=name,
        canonical_name=name,
        kind=TypeKindIR.BUILTIN,
        canonical_kind=TypeKindIR.BUILTIN,
        nullability=NullabilityIR.NON_NULL,
    )


def _field(name: str, type_ref: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=_SPAN,
        value_type=type_ref,
        name=name,
        qualifier=(),
        field=FieldId(_OWNER, name),
    )


def _leaf_names(expression: ExpressionIR) -> list[str]:
    return [leaf.field for leaf in _field_leaves(expression)]


def test_metadata_reader_retains_new_expression_children_in_source_order() -> None:
    int_type = _type("Int")
    bool_type = _type("Bool")

    conditional = ConditionalIR(
        span=_SPAN,
        value_type=int_type,
        when_true=_field("when_true", int_type),
        condition=_field("condition", bool_type),
        when_false=_field("when_false", int_type),
    )
    membership = MembershipIR(
        span=_SPAN,
        value_type=bool_type,
        value=_field("value", int_type),
        options=(_field("first", int_type), _field("second", int_type)),
        negated=False,
    )
    cast = CastIR(
        span=_SPAN,
        value_type=_type("Float"),
        value=_field("cast_value", int_type),
        target=_type("Float"),
    )

    assert _leaf_names(conditional) == ["when_true", "condition", "when_false"]
    assert _leaf_names(membership) == ["value", "first", "second"]
    assert _leaf_names(cast) == ["cast_value"]
