from __future__ import annotations

import ast
import inspect
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast


import pytest

import pietto.semantic.nullability_formulas as nullability_formulas
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    GenericSignature,
    LogicalTypeIdentity,
    ParameterDefault,
    SignatureMatch,
    SignatureParameter,
    TypeVariable,
    VariableTypeExpression,
    bind_signature,
)
from pietto.semantic.model import EffectiveNullability, TypeKind
from pietto.semantic.nullability_formulas import (
    AlwaysNullableFormula,
    AnyNullableFormula,
    AnyOfFormula,
    NonNullFormula,
    NullabilityArgumentEvidence,
    NullabilityDefaultEvidence,
    NullabilityEvaluationContext,
    NullabilityEvaluationEvidence,
    NullabilityEvaluationFailureReason,
    NullabilityEvaluationMatch,
    NullabilityEvaluationUnsupported,
    NullabilityFormula,
    NullabilityFormulaKind,
    NullableFormula,
    NullableIfDefaultOmittedFormula,
    SameAsArgumentFormula,
    SignatureResultFormula,
    evaluate_signature_result_nullability,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/nullability_formulas.py"
INT = LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)
TEXT = LogicalTypeIdentity(name="Text", kind=TypeKind.BUILTIN)


def _simple_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _two_parameter_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
            SignatureParameter(
                position=1,
                type_expression=ConcreteTypeExpression(logical_type=INT),
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _navigation_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
            SignatureParameter(
                position=1,
                type_expression=ConcreteTypeExpression(logical_type=INT),
                optional=True,
            ),
            SignatureParameter(
                position=2,
                type_expression=VariableTypeExpression(name="T"),
                optional=True,
                default=ParameterDefault.OMITTED,
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _optional_without_default_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
            SignatureParameter(
                position=1,
                type_expression=VariableTypeExpression(name="T"),
                optional=True,
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _match(
    formula: NullabilityFormula,
    context: NullabilityEvaluationContext,
    *,
    signature: GenericSignature | None = None,
) -> NullabilityEvaluationMatch:
    association = SignatureResultFormula(
        signature=signature or _simple_signature(),
        nullability=formula,
    )
    result = evaluate_signature_result_nullability(association, context)
    assert type(result) is NullabilityEvaluationMatch
    return cast(NullabilityEvaluationMatch, result)


def _join(
    left: EffectiveNullability,
    right: EffectiveNullability,
) -> EffectiveNullability:
    if EffectiveNullability.NULLABLE in {left, right}:
        return EffectiveNullability.NULLABLE
    if EffectiveNullability.UNKNOWN in {left, right}:
        return EffectiveNullability.UNKNOWN
    return EffectiveNullability.NON_NULL


def _navigation_formula() -> AnyOfFormula:
    return AnyOfFormula(
        children=(
            AnyNullableFormula(argument_indices=(0, 2)),
            NullableIfDefaultOmittedFormula(parameter_index=2),
        )
    )


def test_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert nullability_formulas.__all__ == ()
    carrier_types = (
        NonNullFormula,
        NullableFormula,
        SameAsArgumentFormula,
        AnyNullableFormula,
        AlwaysNullableFormula,
        NullableIfDefaultOmittedFormula,
        AnyOfFormula,
        SignatureResultFormula,
        NullabilityEvaluationContext,
        NullabilityArgumentEvidence,
        NullabilityDefaultEvidence,
        NullabilityEvaluationEvidence,
        NullabilityEvaluationMatch,
        NullabilityEvaluationUnsupported,
    )
    for carrier_type in carrier_types:
        assert is_dataclass(carrier_type)
        assert getattr(carrier_type, "__dataclass_params__").frozen is True
        assert "__dict__" not in carrier_type.__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier_type).parameters.values()
        )
    tree = ast.parse(SOURCE_PATH.read_text())
    imported_modules = tuple(
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
    )
    assert imported_modules == (
        "dataclasses",
        "enum",
        "pietto.semantic.generic_compatibility",
        "pietto.semantic.model",
    )


def test_formula_kind_values_and_union_inventory_are_exact() -> None:
    assert tuple(NullabilityFormulaKind) == (
        NullabilityFormulaKind.NON_NULL,
        NullabilityFormulaKind.NULLABLE,
        NullabilityFormulaKind.SAME_AS_ARG,
        NullabilityFormulaKind.ANY_NULLABLE,
        NullabilityFormulaKind.ALWAYS_NULLABLE,
        NullabilityFormulaKind.NULLABLE_IF_DEFAULT_OMITTED,
        NullabilityFormulaKind.ANY_OF,
    )
    assert tuple(kind.value for kind in NullabilityFormulaKind) == (
        "non_null",
        "nullable",
        "same_as_arg",
        "any_nullable",
        "always_nullable",
        "nullable_if_default_omitted",
        "any_of",
    )
    variants = (
        NonNullFormula,
        NullableFormula,
        SameAsArgumentFormula,
        AnyNullableFormula,
        AlwaysNullableFormula,
        NullableIfDefaultOmittedFormula,
        AnyOfFormula,
    )
    assert (
        tuple(
            field.name
            for variant in variants
            for field in fields(variant)
            if field.name == "kind"
        )
        == ("kind",) * 7
    )
    assert all(
        next(field for field in fields(variant) if field.name == "kind").init is False
        for variant in variants
    )
    source = SOURCE_PATH.read_text()
    assert "ALL_OF" not in source
    assert "class NullabilityFormulaKind" in source


@pytest.mark.parametrize(
    ("formula", "kind", "expected"),
    (
        (
            NonNullFormula(),
            NullabilityFormulaKind.NON_NULL,
            EffectiveNullability.NON_NULL,
        ),
        (
            NullableFormula(),
            NullabilityFormulaKind.NULLABLE,
            EffectiveNullability.NULLABLE,
        ),
        (
            AlwaysNullableFormula(),
            NullabilityFormulaKind.ALWAYS_NULLABLE,
            EffectiveNullability.NULLABLE,
        ),
    ),
    ids=("non-null", "nullable", "always-nullable"),
)
def test_constant_formulas_evaluate_with_distinct_ordered_evidence(
    formula: NullabilityFormula,
    kind: NullabilityFormulaKind,
    expected: EffectiveNullability,
) -> None:
    match = _match(
        formula,
        NullabilityEvaluationContext(
            argument_nullabilities=(EffectiveNullability.NON_NULL,),
            omitted_positions=(),
        ),
    )
    assert match == NullabilityEvaluationMatch(
        value=expected,
        evidence=NullabilityEvaluationEvidence(kind=kind, value=expected),
    )


def test_nullable_and_always_nullable_are_distinct_structural_identities() -> None:
    nullable = NullableFormula()
    always = AlwaysNullableFormula()
    assert type(nullable) is not type(always)
    assert nullable != always
    assert nullable.kind is NullabilityFormulaKind.NULLABLE
    assert always.kind is NullabilityFormulaKind.ALWAYS_NULLABLE
    assert repr(nullable) != repr(always)
    assert {
        _match(
            formula,
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.UNKNOWN,),
                omitted_positions=(),
            ),
        ).value
        for formula in (nullable, always)
    } == {EffectiveNullability.NULLABLE}


@pytest.mark.parametrize(
    ("carrier", "case", "expected"),
    (
        ("same", "wrong", TypeError),
        ("same", "bool", TypeError),
        ("same", "negative", ValueError),
        ("default", "wrong", TypeError),
        ("default", "bool", TypeError),
        ("default", "negative", ValueError),
    ),
)
def test_argument_index_scalar_validation_is_exact(
    carrier: str,
    case: str,
    expected: type[Exception],
) -> None:
    value: object = "0" if case == "wrong" else True if case == "bool" else -1
    with pytest.raises(expected):
        if carrier == "same":
            SameAsArgumentFormula(argument_index=cast(int, value))
        else:
            NullableIfDefaultOmittedFormula(parameter_index=cast(int, value))


@pytest.mark.parametrize(
    "case",
    ("one", "ordered", "duplicate", "empty", "too-many", "containers", "members"),
)
def test_any_nullable_index_tuple_order_duplicates_and_bounds_are_exact(
    case: str,
) -> None:
    if case == "one":
        assert AnyNullableFormula(argument_indices=(1,)).argument_indices == (1,)
    elif case == "ordered":
        assert AnyNullableFormula(argument_indices=(1, 0)).argument_indices == (1, 0)
    elif case == "duplicate":
        assert AnyNullableFormula(argument_indices=(0, 0)).argument_indices == (0, 0)
    elif case == "empty":
        with pytest.raises(ValueError):
            AnyNullableFormula(argument_indices=())
    elif case == "too-many":
        with pytest.raises(ValueError):
            AnyNullableFormula(argument_indices=(0, 1, 2))
    elif case == "containers":
        for value in ([0], {0}, {"position": 0}):
            with pytest.raises(TypeError):
                AnyNullableFormula(argument_indices=cast(tuple[int, ...], value))
    else:
        for value in ((True,), (-1,), ("0",)):
            with pytest.raises((TypeError, ValueError)):
                AnyNullableFormula(argument_indices=cast(tuple[int, ...], value))


@pytest.mark.parametrize(
    "case",
    ("ordered", "reverse", "duplicate", "empty", "one", "three", "invalid"),
)
def test_any_of_child_tuple_order_duplicates_and_arity_are_exact(case: str) -> None:
    left = NonNullFormula()
    right = NullableFormula()
    if case == "ordered":
        assert AnyOfFormula(children=(left, right)).children == (left, right)
    elif case == "reverse":
        assert AnyOfFormula(children=(right, left)).children == (right, left)
    elif case == "duplicate":
        assert AnyOfFormula(children=(left, left)).children == (left, left)
    elif case == "empty":
        with pytest.raises(ValueError):
            AnyOfFormula(
                children=cast(tuple[NullabilityFormula, NullabilityFormula], ())
            )
    elif case == "one":
        with pytest.raises(ValueError):
            AnyOfFormula(
                children=cast(tuple[NullabilityFormula, NullabilityFormula], (left,))
            )
    elif case == "three":
        with pytest.raises(ValueError):
            AnyOfFormula(
                children=cast(
                    tuple[NullabilityFormula, NullabilityFormula], (left, right, left)
                )
            )
    else:
        for value in ([left, right], {left, right}, (left, object())):
            with pytest.raises(TypeError):
                AnyOfFormula(
                    children=cast(tuple[NullabilityFormula, NullabilityFormula], value)
                )


@pytest.mark.parametrize(
    "case",
    ("leaf", "maximum", "nested-left", "nested-right", "three-refs", "four-refs"),
)
def test_formula_depth_node_and_child_bounds_are_exact(case: str) -> None:
    signature = _navigation_signature()
    if case == "leaf":
        assert (
            SignatureResultFormula(
                signature=signature, nullability=NonNullFormula()
            ).nullability
            == NonNullFormula()
        )
    elif case == "maximum":
        assert (
            SignatureResultFormula(
                signature=signature, nullability=_navigation_formula()
            ).nullability
            == _navigation_formula()
        )
    elif case == "nested-left":
        nested = AnyOfFormula(
            children=(
                AnyOfFormula(children=(NonNullFormula(), NullableFormula())),
                NonNullFormula(),
            )
        )
        with pytest.raises(ValueError, match="depth"):
            SignatureResultFormula(signature=signature, nullability=nested)
    elif case == "nested-right":
        nested = AnyOfFormula(
            children=(
                NonNullFormula(),
                AnyOfFormula(children=(NullableFormula(), NonNullFormula())),
            )
        )
        with pytest.raises(ValueError, match="depth"):
            SignatureResultFormula(signature=signature, nullability=nested)
    elif case == "three-refs":
        formula = AnyOfFormula(
            children=(
                AnyNullableFormula(argument_indices=(0, 2)),
                SameAsArgumentFormula(argument_index=0),
            )
        )
        with pytest.raises(ValueError, match="references"):
            SignatureResultFormula(signature=signature, nullability=formula)
    else:
        formula = AnyOfFormula(
            children=(
                AnyNullableFormula(argument_indices=(0, 2)),
                AnyNullableFormula(argument_indices=(0, 2)),
            )
        )
        with pytest.raises(ValueError, match="references"):
            SignatureResultFormula(signature=signature, nullability=formula)


@pytest.mark.parametrize("value", tuple(EffectiveNullability))
def test_same_as_argument_three_state_truth_table_is_exact(
    value: EffectiveNullability,
) -> None:
    match = _match(
        SameAsArgumentFormula(argument_index=0),
        NullabilityEvaluationContext(
            argument_nullabilities=(value,), omitted_positions=()
        ),
    )
    assert match.value is value
    assert match.evidence == NullabilityEvaluationEvidence(
        kind=NullabilityFormulaKind.SAME_AS_ARG,
        value=value,
        arguments=(
            NullabilityArgumentEvidence(
                parameter_position=0, supplied=True, value=value, contribution=value
            ),
        ),
    )


@pytest.mark.parametrize("indices", ((0,), (0, 1), (1, 0), (0, 0)))
def test_any_nullable_all_non_null_and_ordered_evidence_are_exact(
    indices: tuple[int, ...],
) -> None:
    match = _match(
        AnyNullableFormula(argument_indices=indices),
        NullabilityEvaluationContext(
            argument_nullabilities=(
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
            ),
            omitted_positions=(),
        ),
        signature=_two_parameter_signature(),
    )
    assert match.value is EffectiveNullability.NON_NULL
    assert (
        tuple(item.parameter_position for item in match.evidence.arguments) == indices
    )
    assert all(
        item.contribution is EffectiveNullability.NON_NULL
        for item in match.evidence.arguments
    )


@pytest.mark.parametrize(
    "values",
    (
        (EffectiveNullability.NULLABLE,),
        (EffectiveNullability.NULLABLE, EffectiveNullability.NON_NULL),
        (EffectiveNullability.NON_NULL, EffectiveNullability.NULLABLE),
        (EffectiveNullability.NULLABLE, EffectiveNullability.UNKNOWN),
        (EffectiveNullability.UNKNOWN, EffectiveNullability.NULLABLE),
        (EffectiveNullability.NULLABLE, EffectiveNullability.NULLABLE),
    ),
)
def test_any_nullable_nullable_precedence_is_exact(
    values: tuple[EffectiveNullability, ...],
) -> None:
    indices = tuple(range(len(values)))
    signature = _simple_signature() if len(values) == 1 else _two_parameter_signature()
    match = _match(
        AnyNullableFormula(argument_indices=indices),
        NullabilityEvaluationContext(
            argument_nullabilities=values, omitted_positions=()
        ),
        signature=signature,
    )
    assert match.value is EffectiveNullability.NULLABLE
    assert tuple(item.value for item in match.evidence.arguments) == values


@pytest.mark.parametrize(
    ("values", "indices"),
    (
        ((EffectiveNullability.UNKNOWN,), (0,)),
        (
            (EffectiveNullability.UNKNOWN, EffectiveNullability.NON_NULL),
            (0, 1),
        ),
        (
            (EffectiveNullability.NON_NULL, EffectiveNullability.UNKNOWN),
            (0, 1),
        ),
        (
            (EffectiveNullability.UNKNOWN, EffectiveNullability.UNKNOWN),
            (0, 1),
        ),
        (
            (EffectiveNullability.UNKNOWN, EffectiveNullability.NON_NULL),
            (0, 0),
        ),
    ),
)
def test_any_nullable_unknown_precedence_is_exact(
    values: tuple[EffectiveNullability, ...],
    indices: tuple[int, ...],
) -> None:
    signature = _simple_signature() if len(values) == 1 else _two_parameter_signature()
    match = _match(
        AnyNullableFormula(argument_indices=indices),
        NullabilityEvaluationContext(
            argument_nullabilities=values, omitted_positions=()
        ),
        signature=signature,
    )
    assert match.value is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize("omitted", (False, True), ids=("supplied", "omitted"))
def test_default_omission_formula_supplied_and_omitted_results_are_exact(
    omitted: bool,
) -> None:
    context = NullabilityEvaluationContext(
        argument_nullabilities=(
            (EffectiveNullability.NON_NULL, EffectiveNullability.NON_NULL)
            if omitted
            else (
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
                EffectiveNullability.UNKNOWN,
            )
        ),
        omitted_positions=(2,) if omitted else (),
    )
    match = _match(
        NullableIfDefaultOmittedFormula(parameter_index=2),
        context,
        signature=_navigation_signature(),
    )
    expected = (
        EffectiveNullability.NULLABLE if omitted else EffectiveNullability.NON_NULL
    )
    assert match == NullabilityEvaluationMatch(
        value=expected,
        evidence=NullabilityEvaluationEvidence(
            kind=NullabilityFormulaKind.NULLABLE_IF_DEFAULT_OMITTED,
            value=expected,
            default=NullabilityDefaultEvidence(
                parameter_position=2, omitted=omitted, contribution=expected
            ),
        ),
    )


@pytest.mark.parametrize(
    ("left", "right"),
    tuple(
        (left, right) for left in EffectiveNullability for right in EffectiveNullability
    ),
)
def test_any_of_complete_three_state_truth_table_is_exact(
    left: EffectiveNullability,
    right: EffectiveNullability,
) -> None:
    formula = AnyOfFormula(
        children=(
            SameAsArgumentFormula(argument_index=0),
            SameAsArgumentFormula(argument_index=1),
        )
    )
    match = _match(
        formula,
        NullabilityEvaluationContext(
            argument_nullabilities=(left, right), omitted_positions=()
        ),
        signature=_two_parameter_signature(),
    )
    assert match.value is _join(left, right)
    assert tuple(child.value for child in match.evidence.children) == (left, right)


@pytest.mark.parametrize(
    "case", ("match-order", "duplicate", "unsupported-first", "unsupported-second")
)
def test_any_of_evaluates_every_child_in_declared_order(case: str) -> None:
    signature = _navigation_signature()
    if case == "match-order":
        result = _match(
            AnyOfFormula(children=(NullableFormula(), NonNullFormula())),
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.NON_NULL,),
                omitted_positions=(1, 2),
            ),
            signature=signature,
        )
        assert tuple(child.kind for child in result.evidence.children) == (
            NullabilityFormulaKind.NULLABLE,
            NullabilityFormulaKind.NON_NULL,
        )
    elif case == "duplicate":
        result = _match(
            AnyOfFormula(children=(AlwaysNullableFormula(), AlwaysNullableFormula())),
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.NON_NULL,),
                omitted_positions=(1, 2),
            ),
            signature=signature,
        )
        assert (
            tuple(child.kind for child in result.evidence.children)
            == (NullabilityFormulaKind.ALWAYS_NULLABLE,) * 2
        )
    else:
        omitted = SameAsArgumentFormula(argument_index=2)
        supplied = SameAsArgumentFormula(argument_index=0)
        formula = AnyOfFormula(
            children=(omitted, supplied)
            if case == "unsupported-first"
            else (supplied, omitted)
        )
        outcome = evaluate_signature_result_nullability(
            SignatureResultFormula(signature=signature, nullability=formula),
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.UNKNOWN,),
                omitted_positions=(1, 2),
            ),
        )
        assert outcome == NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.OMITTED_ARGUMENT_REFERENCED,
            parameter_position=2,
        )
        assert "child_results = tuple(" in SOURCE_PATH.read_text()


@pytest.mark.parametrize(
    "case",
    (
        "arguments-container",
        "argument-member",
        "omissions-container",
        "omission-bool",
        "omission-negative",
        "omission-duplicate",
        "omission-unsorted",
        "valid",
    ),
)
def test_evaluation_context_container_member_and_order_shapes_are_exact(
    case: str,
) -> None:
    if case == "arguments-container":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=cast(tuple[EffectiveNullability, ...], []),
                omitted_positions=(),
            )
    elif case == "argument-member":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=cast(
                    tuple[EffectiveNullability, ...], ("unknown",)
                ),
                omitted_positions=(),
            )
    elif case == "omissions-container":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=cast(tuple[int, ...], [])
            )
    elif case == "omission-bool":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(cast(int, True),)
            )
    elif case == "omission-negative":
        with pytest.raises(ValueError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(-1,)
            )
    elif case == "omission-duplicate":
        with pytest.raises(ValueError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(1, 1)
            )
    elif case == "omission-unsorted":
        with pytest.raises(ValueError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(2, 1)
            )
    else:
        context = NullabilityEvaluationContext(
            argument_nullabilities=(EffectiveNullability.UNKNOWN,),
            omitted_positions=(1, 2),
        )
        assert context.argument_nullabilities == (EffectiveNullability.UNKNOWN,)
        assert context.omitted_positions == (1, 2)


@pytest.mark.parametrize(
    "case", ("non-null", "nullable", "always", "same", "any-nullable", "composed")
)
def test_signature_result_wrapper_accepts_valid_formula_references(case: str) -> None:
    formulas: dict[str, NullabilityFormula] = {
        "non-null": NonNullFormula(),
        "nullable": NullableFormula(),
        "always": AlwaysNullableFormula(),
        "same": SameAsArgumentFormula(argument_index=0),
        "any-nullable": AnyNullableFormula(argument_indices=(0, 2)),
        "composed": _navigation_formula(),
    }
    formula = formulas[case]
    association = SignatureResultFormula(
        signature=_navigation_signature(), nullability=formula
    )
    assert association.signature == _navigation_signature()
    assert association.nullability == formula


@pytest.mark.parametrize("case", ("same", "any-first", "any-second", "default"))
def test_signature_result_wrapper_rejects_out_of_range_references(case: str) -> None:
    formulas: dict[str, NullabilityFormula] = {
        "same": SameAsArgumentFormula(argument_index=3),
        "any-first": AnyNullableFormula(argument_indices=(3,)),
        "any-second": AnyNullableFormula(argument_indices=(0, 3)),
        "default": NullableIfDefaultOmittedFormula(parameter_index=3),
    }
    with pytest.raises(ValueError, match="outside"):
        SignatureResultFormula(
            signature=_navigation_signature(), nullability=formulas[case]
        )


@pytest.mark.parametrize(
    "case",
    (
        "valid-leaf",
        "valid-composed",
        "required",
        "optional-no-marker",
        "duplicate-default",
    ),
)
def test_default_reference_requires_optional_omitted_marker(case: str) -> None:
    if case == "valid-leaf":
        association = SignatureResultFormula(
            signature=_navigation_signature(),
            nullability=NullableIfDefaultOmittedFormula(parameter_index=2),
        )
        assert association.nullability == NullableIfDefaultOmittedFormula(
            parameter_index=2
        )
    elif case == "valid-composed":
        assert (
            SignatureResultFormula(
                signature=_navigation_signature(), nullability=_navigation_formula()
            ).nullability
            == _navigation_formula()
        )
    elif case == "required":
        with pytest.raises(ValueError, match="optional"):
            SignatureResultFormula(
                signature=_two_parameter_signature(),
                nullability=NullableIfDefaultOmittedFormula(parameter_index=1),
            )
    elif case == "optional-no-marker":
        with pytest.raises(ValueError, match="ParameterDefault.OMITTED"):
            SignatureResultFormula(
                signature=_optional_without_default_signature(),
                nullability=NullableIfDefaultOmittedFormula(parameter_index=1),
            )
    else:
        formula = AnyOfFormula(
            children=(
                NullableIfDefaultOmittedFormula(parameter_index=2),
                NullableIfDefaultOmittedFormula(parameter_index=2),
            )
        )
        association = SignatureResultFormula(
            signature=_navigation_signature(), nullability=formula
        )
        assert association.nullability == formula


@pytest.mark.parametrize(
    ("case", "arguments", "omissions", "reason", "position"),
    (
        (
            "too-many",
            (EffectiveNullability.NON_NULL,) * 4,
            (),
            NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH,
            None,
        ),
        (
            "required",
            (),
            (0, 1, 2),
            NullabilityEvaluationFailureReason.REQUIRED_PARAMETER_OMITTED,
            0,
        ),
        (
            "missing-first",
            (EffectiveNullability.NON_NULL,),
            (2,),
            NullabilityEvaluationFailureReason.MISSING_ARGUMENT_NULLABILITY,
            1,
        ),
        (
            "missing-second",
            (EffectiveNullability.NON_NULL,),
            (1,),
            NullabilityEvaluationFailureReason.MISSING_ARGUMENT_NULLABILITY,
            2,
        ),
        (
            "out-of-range-extra",
            (EffectiveNullability.NON_NULL,) * 2,
            (2, 3),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            3,
        ),
        (
            "supplied-extra",
            (EffectiveNullability.NON_NULL,) * 2,
            (1, 2),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            1,
        ),
        (
            "full-out-of-range",
            (EffectiveNullability.NON_NULL,) * 3,
            (3,),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            3,
        ),
        (
            "full-supplied",
            (EffectiveNullability.NON_NULL,) * 3,
            (2,),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            2,
        ),
    ),
)
def test_incompatible_contexts_return_ordered_structured_unsupported(
    case: str,
    arguments: tuple[EffectiveNullability, ...],
    omissions: tuple[int, ...],
    reason: NullabilityEvaluationFailureReason,
    position: int | None,
) -> None:
    del case
    result = evaluate_signature_result_nullability(
        SignatureResultFormula(
            signature=_navigation_signature(), nullability=NonNullFormula()
        ),
        NullabilityEvaluationContext(
            argument_nullabilities=arguments, omitted_positions=omissions
        ),
    )
    assert result == NullabilityEvaluationUnsupported(
        reason=reason, parameter_position=position
    )


@pytest.mark.parametrize(
    ("case", "value", "expected"),
    (
        ("same", EffectiveNullability.NON_NULL, None),
        ("any-non-null", EffectiveNullability.NON_NULL, EffectiveNullability.NON_NULL),
        ("any-unknown", EffectiveNullability.UNKNOWN, EffectiveNullability.UNKNOWN),
        ("any-nullable", EffectiveNullability.NULLABLE, EffectiveNullability.NULLABLE),
    ),
)
def test_omitted_same_as_arg_fails_closed_and_any_nullable_is_neutral(
    case: str,
    value: EffectiveNullability,
    expected: EffectiveNullability | None,
) -> None:
    context = NullabilityEvaluationContext(
        argument_nullabilities=(value,), omitted_positions=(1, 2)
    )
    signature = _navigation_signature()
    if case == "same":
        result = evaluate_signature_result_nullability(
            SignatureResultFormula(
                signature=signature, nullability=SameAsArgumentFormula(argument_index=2)
            ),
            context,
        )
        assert result == NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.OMITTED_ARGUMENT_REFERENCED,
            parameter_position=2,
        )
    else:
        match = _match(
            AnyNullableFormula(argument_indices=(0, 2)),
            context,
            signature=signature,
        )
        assert match.value is expected
        assert match.evidence.arguments[1] == NullabilityArgumentEvidence(
            parameter_position=2,
            supplied=False,
            value=None,
            contribution=EffectiveNullability.NON_NULL,
        )


@pytest.mark.parametrize(
    "case",
    (
        "argument-supplied",
        "argument-omitted",
        "supplied-none",
        "supplied-mismatch",
        "omitted-value",
        "omitted-contribution",
        "default-mismatch",
        "evidence-shape",
    ),
)
def test_evaluation_evidence_carrier_invariants_are_exact(case: str) -> None:
    if case == "argument-supplied":
        row = NullabilityArgumentEvidence(
            parameter_position=0,
            supplied=True,
            value=EffectiveNullability.UNKNOWN,
            contribution=EffectiveNullability.UNKNOWN,
        )
        assert row.value is row.contribution
    elif case == "argument-omitted":
        row = NullabilityArgumentEvidence(
            parameter_position=2,
            supplied=False,
            value=None,
            contribution=EffectiveNullability.NON_NULL,
        )
        assert row.value is None
    elif case == "supplied-none":
        with pytest.raises(TypeError):
            NullabilityArgumentEvidence(
                parameter_position=0,
                supplied=True,
                value=None,
                contribution=EffectiveNullability.NON_NULL,
            )
    elif case == "supplied-mismatch":
        with pytest.raises(ValueError):
            NullabilityArgumentEvidence(
                parameter_position=0,
                supplied=True,
                value=EffectiveNullability.UNKNOWN,
                contribution=EffectiveNullability.NON_NULL,
            )
    elif case == "omitted-value":
        with pytest.raises(ValueError):
            NullabilityArgumentEvidence(
                parameter_position=2,
                supplied=False,
                value=EffectiveNullability.UNKNOWN,
                contribution=EffectiveNullability.NON_NULL,
            )
    elif case == "omitted-contribution":
        with pytest.raises(ValueError):
            NullabilityArgumentEvidence(
                parameter_position=2,
                supplied=False,
                value=None,
                contribution=EffectiveNullability.UNKNOWN,
            )
    elif case == "default-mismatch":
        with pytest.raises(ValueError):
            NullabilityDefaultEvidence(
                parameter_position=2,
                omitted=True,
                contribution=EffectiveNullability.NON_NULL,
            )
    else:
        with pytest.raises(ValueError):
            NullabilityEvaluationEvidence(
                kind=NullabilityFormulaKind.ANY_OF,
                value=EffectiveNullability.NON_NULL,
            )


@pytest.mark.parametrize(
    "case",
    (
        "arity-valid",
        "arity-position",
        "required-position",
        "invalid-none",
        "wrong-reason",
    ),
)
def test_evaluation_unsupported_carrier_invariants_are_exact(case: str) -> None:
    if case == "arity-valid":
        result = NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH
        )
        assert result.parameter_position is None
    elif case == "arity-position":
        with pytest.raises(ValueError):
            NullabilityEvaluationUnsupported(
                reason=NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH,
                parameter_position=0,
            )
    elif case == "required-position":
        with pytest.raises(ValueError):
            NullabilityEvaluationUnsupported(
                reason=NullabilityEvaluationFailureReason.REQUIRED_PARAMETER_OMITTED
            )
    elif case == "invalid-none":
        with pytest.raises(ValueError):
            NullabilityEvaluationUnsupported(
                reason=NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT
            )
    else:
        with pytest.raises(TypeError):
            NullabilityEvaluationUnsupported(
                reason=cast(NullabilityEvaluationFailureReason, "invalid")
            )


@pytest.mark.parametrize("case", ("formula", "wrapper", "context", "result"))
def test_formula_result_and_evidence_equality_hash_repr_are_repeatable(
    case: str,
) -> None:
    formula = _navigation_formula()
    wrapper = SignatureResultFormula(
        signature=_navigation_signature(), nullability=formula
    )
    context = NullabilityEvaluationContext(
        argument_nullabilities=(EffectiveNullability.UNKNOWN,),
        omitted_positions=(1, 2),
    )
    result = evaluate_signature_result_nullability(wrapper, context)
    values: dict[str, object] = {
        "formula": formula,
        "wrapper": wrapper,
        "context": context,
        "result": result,
    }
    value = values[case]
    assert value == value
    assert hash(value) == hash(value)
    assert repr(value) == repr(value)
    assert "object at" not in repr(value)


@pytest.mark.parametrize("value", tuple(EffectiveNullability))
def test_lag_lead_omitted_default_readiness_formula_is_exact(
    value: EffectiveNullability,
) -> None:
    match = _match(
        _navigation_formula(),
        NullabilityEvaluationContext(
            argument_nullabilities=(value,), omitted_positions=(1, 2)
        ),
        signature=_navigation_signature(),
    )
    assert match.value is EffectiveNullability.NULLABLE
    any_nullable, omission = match.evidence.children
    assert any_nullable.arguments == (
        NullabilityArgumentEvidence(
            parameter_position=0, supplied=True, value=value, contribution=value
        ),
        NullabilityArgumentEvidence(
            parameter_position=2,
            supplied=False,
            value=None,
            contribution=EffectiveNullability.NON_NULL,
        ),
    )
    assert omission.default == NullabilityDefaultEvidence(
        parameter_position=2,
        omitted=True,
        contribution=EffectiveNullability.NULLABLE,
    )


@pytest.mark.parametrize(
    ("value", "default"),
    tuple(
        (value, default)
        for value in EffectiveNullability
        for default in EffectiveNullability
    ),
)
def test_lag_lead_supplied_default_truth_matrix_is_exact(
    value: EffectiveNullability,
    default: EffectiveNullability,
) -> None:
    match = _match(
        _navigation_formula(),
        NullabilityEvaluationContext(
            argument_nullabilities=(value, EffectiveNullability.UNKNOWN, default),
            omitted_positions=(),
        ),
        signature=_navigation_signature(),
    )
    assert match.value is _join(value, default)
    any_nullable, omission = match.evidence.children
    assert tuple(row.parameter_position for row in any_nullable.arguments) == (0, 2)
    assert tuple(row.value for row in any_nullable.arguments) == (value, default)
    assert omission.default == NullabilityDefaultEvidence(
        parameter_position=2,
        omitted=False,
        contribution=EffectiveNullability.NON_NULL,
    )


@pytest.mark.parametrize("navigation_name", ("lag", "lead"))
def test_lag_and_lead_readiness_associations_are_identity_free(
    navigation_name: str,
) -> None:
    association = SignatureResultFormula(
        signature=_navigation_signature(),
        nullability=_navigation_formula(),
    )
    assert association == SignatureResultFormula(
        signature=_navigation_signature(),
        nullability=_navigation_formula(),
    )
    assert navigation_name not in {field.name for field in fields(association)}
    assert tuple(field.name for field in fields(association)) == (
        "signature",
        "nullability",
    )


@pytest.mark.parametrize(
    ("arguments", "facts", "expected_omitted", "expected_value"),
    (
        (
            (TEXT,),
            (EffectiveNullability.NON_NULL,),
            (1, 2),
            EffectiveNullability.NULLABLE,
        ),
        (
            (TEXT, INT),
            (EffectiveNullability.NON_NULL, EffectiveNullability.NON_NULL),
            (2,),
            EffectiveNullability.NULLABLE,
        ),
        (
            (TEXT, INT, TEXT),
            (
                EffectiveNullability.UNKNOWN,
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
            ),
            (),
            EffectiveNullability.UNKNOWN,
        ),
        (
            (INT, INT, INT),
            (
                EffectiveNullability.NULLABLE,
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
            ),
            (),
            EffectiveNullability.NULLABLE,
        ),
    ),
)
def test_signature_match_omissions_compose_without_type_binding_changes(
    arguments: tuple[LogicalTypeIdentity, ...],
    facts: tuple[EffectiveNullability, ...],
    expected_omitted: tuple[int, ...],
    expected_value: EffectiveNullability,
) -> None:
    signature = _navigation_signature()
    binding = bind_signature(signature, arguments)
    assert type(binding) is SignatureMatch
    match = cast(SignatureMatch, binding)
    assert match.result_type == arguments[0]
    assert match.omitted_positions == expected_omitted
    result = _match(
        _navigation_formula(),
        NullabilityEvaluationContext(
            argument_nullabilities=facts,
            omitted_positions=match.omitted_positions,
        ),
        signature=signature,
    )
    assert result.value is expected_value


def test_current_semantic_analyzer_and_window_paths_do_not_import_nullability_formulas() -> (
    None
):
    protected_consumers = (
        "src/pietto/semantic/analyzer.py",
        "src/pietto/semantic/catalog.py",
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/aggregates.py",
        "src/pietto/_window_identity.py",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
    )
    assert all(
        "nullability_formulas" not in (REPO_ROOT / path).read_text()
        for path in protected_consumers
    )
    window_analysis = (REPO_ROOT / "src/pietto/semantic/window_analysis.py").read_text()
    assert "pietto.semantic.nullability_formulas import" in window_analysis
    assert "SignatureResultFormula(" in window_analysis
    assert "nullability=NonNullFormula()" in window_analysis
    source = SOURCE_PATH.read_text()
    assert "pietto.semantic.generic_compatibility import" in source
    assert "pietto.semantic.model import EffectiveNullability" in source
    for forbidden in (
        "analyzer",
        "catalog",
        "capability",
        "_window",
        "_project",
        "pietto.ir",
        "pietto.sql",
        "cli",
        "serializer",
    ):
        assert f"import {forbidden}" not in source
