from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any, cast


import pytest

import pietto
import pietto.semantic as semantic_api
import pietto.semantic.generic_compatibility as generic_compatibility
from pietto.semantic.generic_compatibility import (
    ArityMismatch,
    CandidateEvaluation,
    ConcreteTypeExpression,
    ConcreteTypeMismatch,
    ConstraintEvidence,
    ConstraintMismatch,
    GenericSignature,
    LogicalTypeIdentity,
    OverloadOutcome,
    OverloadSelection,
    OverloadSet,
    ParameterDefault,
    RepeatedVariableMismatch,
    SignatureMatch,
    SignatureParameter,
    SignatureUnsupported,
    TypeConstraint,
    TypeVariable,
    TypeVariableBinding,
    UnboundResult,
    UnresolvedArgument,
    VariableTypeExpression,
    bind_signature,
    select_overload,
    supports_constraint,
)
from pietto.semantic.model import TypeKind


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/generic_compatibility.py"
_MATRIX_ROWS = (
    ("Any", TypeKind.BUILTIN, (True, False, False, False)),
    ("Bool", TypeKind.BUILTIN, (True, True, False, False)),
    ("Bytes", TypeKind.BUILTIN, (True, False, False, False)),
    ("Date", TypeKind.BUILTIN, (True, True, True, False)),
    ("Decimal", TypeKind.BUILTIN, (True, True, True, True)),
    ("Float", TypeKind.BUILTIN, (True, True, True, True)),
    ("Int", TypeKind.BUILTIN, (True, True, True, True)),
    ("Json", TypeKind.BUILTIN, (True, False, False, False)),
    ("Text", TypeKind.BUILTIN, (True, True, False, False)),
    ("Timestamp", TypeKind.BUILTIN, (True, True, True, False)),
    ("UUID", TypeKind.BUILTIN, (True, True, False, False)),
    ("OrderState", TypeKind.ENUM, (False, False, False, False)),
    ("OrderRow", TypeKind.SHAPE, (False, False, False, False)),
    (None, None, (False, False, False, False)),
)
_MATRIX_CASES = tuple(
    (
        name or "unresolved",
        None
        if name is None
        else LogicalTypeIdentity(name=name, kind=cast(TypeKind, kind)),
        constraint,
        expected[index],
    )
    for name, kind, expected in _MATRIX_ROWS
    for index, constraint in enumerate(TypeConstraint)
)

INT = LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)
FLOAT = LogicalTypeIdentity(name="Float", kind=TypeKind.BUILTIN)
DECIMAL = LogicalTypeIdentity(name="Decimal", kind=TypeKind.BUILTIN)
TEXT = LogicalTypeIdentity(name="Text", kind=TypeKind.BUILTIN)
DATE = LogicalTypeIdentity(name="Date", kind=TypeKind.BUILTIN)
BOOL = LogicalTypeIdentity(name="Bool", kind=TypeKind.BUILTIN)
UUID = LogicalTypeIdentity(name="UUID", kind=TypeKind.BUILTIN)


def _concrete_signature(
    parameter_types: tuple[LogicalTypeIdentity, ...],
    result: LogicalTypeIdentity,
    *,
    optional_from: int | None = None,
) -> GenericSignature:
    return GenericSignature(
        type_variables=(),
        parameters=tuple(
            SignatureParameter(
                position=index,
                type_expression=ConcreteTypeExpression(logical_type=logical_type),
                optional=optional_from is not None and index >= optional_from,
            )
            for index, logical_type in enumerate(parameter_types)
        ),
        result=ConcreteTypeExpression(logical_type=result),
    )


def _variable_signature(
    constraints: tuple[TypeConstraint, ...] = (),
    *,
    repeated: bool = False,
    optional: bool = False,
    result: LogicalTypeIdentity | None = None,
) -> GenericSignature:
    variable = TypeVariable(name="T", constraints=constraints)
    expression = VariableTypeExpression(name="T")
    parameters = (
        SignatureParameter(
            position=0,
            type_expression=expression,
            optional=optional,
        ),
    )
    if repeated:
        parameters += (SignatureParameter(position=1, type_expression=expression),)
    result_expression = (
        ConcreteTypeExpression(logical_type=result)
        if result is not None
        else VariableTypeExpression(name="T")
    )
    return GenericSignature(
        type_variables=(variable,),
        parameters=parameters,
        result=result_expression,
    )


def _assert_unsupported(
    result: object,
    mismatch_type: type[object],
) -> object:
    assert type(result) is SignatureUnsupported
    mismatch = cast(SignatureUnsupported, result).mismatch
    assert type(mismatch) is mismatch_type
    return mismatch


def test_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert generic_compatibility.__all__ == ()
    assert tuple(TypeConstraint) == (
        TypeConstraint.SCALAR,
        TypeConstraint.COMPARABLE,
        TypeConstraint.ORDERABLE,
        TypeConstraint.NUMERIC,
    )
    assert tuple(ParameterDefault) == (ParameterDefault.OMITTED,)
    assert tuple(OverloadOutcome) == (
        OverloadOutcome.MATCH,
        OverloadOutcome.UNSUPPORTED,
        OverloadOutcome.AMBIGUOUS,
    )
    assert tuple(member.value for member in TypeConstraint) == (
        "scalar",
        "comparable",
        "orderable",
        "numeric",
    )
    carriers = (
        LogicalTypeIdentity,
        TypeVariable,
        ConcreteTypeExpression,
        VariableTypeExpression,
        SignatureParameter,
        GenericSignature,
        TypeVariableBinding,
        ConstraintEvidence,
        ArityMismatch,
        UnresolvedArgument,
        ConcreteTypeMismatch,
        RepeatedVariableMismatch,
        ConstraintMismatch,
        UnboundResult,
        SignatureMatch,
        SignatureUnsupported,
        OverloadSet,
        CandidateEvaluation,
        OverloadSelection,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert "__slots__" in carrier.__dict__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    source = SOURCE_PATH.read_text()
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert imported == {"annotations", "dataclass", "StrEnum", "TypeKind"}
    assert not hasattr(pietto, "LogicalTypeIdentity")
    assert not hasattr(semantic_api, "LogicalTypeIdentity")
    assert "capability_" not in source
    assert "_window" not in source


@pytest.mark.parametrize(
    "case",
    (
        "builtin",
        "enum",
        "shape",
        "case",
        "equality",
        "name-type",
        "name-pattern",
        "kind-type",
        "kind-value",
        "builtin-name",
    ),
)
def test_logical_type_identity_validation_equality_hash_and_repr_are_exact(
    case: str,
) -> None:
    if case == "builtin":
        assert INT == LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)
    elif case == "enum":
        value = LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM)
        assert (value.name, value.kind) == ("OrderState", TypeKind.ENUM)
    elif case == "shape":
        value = LogicalTypeIdentity(name="OrderRow", kind=TypeKind.SHAPE)
        assert hash(value) == hash(
            LogicalTypeIdentity(name="OrderRow", kind=TypeKind.SHAPE)
        )
    elif case == "case":
        upper = LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM)
        lower = LogicalTypeIdentity(name="orderState", kind=TypeKind.ENUM)
        assert upper != lower
    elif case == "equality":
        assert len({INT, LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)}) == 1
        assert "name='Int'" in repr(INT)
        assert "TypeKind.BUILTIN" in repr(INT)
    elif case == "name-type":
        with pytest.raises(TypeError, match="logical type name must be an exact str"):
            LogicalTypeIdentity(name=cast(Any, 1), kind=TypeKind.ENUM)
    elif case == "name-pattern":
        with pytest.raises(ValueError, match="logical type name must match"):
            LogicalTypeIdentity(name="not-valid", kind=TypeKind.ENUM)
    elif case == "kind-type":
        with pytest.raises(
            TypeError, match="logical type kind must be an exact TypeKind"
        ):
            LogicalTypeIdentity(name="Int", kind=cast(Any, "builtin"))
    elif case == "kind-value":
        with pytest.raises(ValueError, match="must be BUILTIN, ENUM, or SHAPE"):
            LogicalTypeIdentity(name="Alias", kind=TypeKind.TYPE_ALIAS)
    else:
        with pytest.raises(ValueError, match="not in the exact catalog"):
            LogicalTypeIdentity(name="Integer", kind=TypeKind.BUILTIN)


@pytest.mark.parametrize(
    "case",
    (
        "empty",
        "ordered",
        "case",
        "name-type",
        "name-pattern",
        "container",
        "member",
        "duplicate",
        "frozen",
        "repr",
    ),
)
def test_type_variable_name_and_constraint_validation_is_exact(case: str) -> None:
    if case == "empty":
        assert TypeVariable(name="T", constraints=()).constraints == ()
    elif case == "ordered":
        value = TypeVariable(
            name="T",
            constraints=(TypeConstraint.NUMERIC, TypeConstraint.SCALAR),
        )
        assert value.constraints == (TypeConstraint.NUMERIC, TypeConstraint.SCALAR)
    elif case == "case":
        assert TypeVariable(name="T", constraints=()) != TypeVariable(
            name="t",
            constraints=(),
        )
    elif case == "name-type":
        with pytest.raises(TypeError, match="type variable name must be an exact str"):
            TypeVariable(name=cast(Any, 1), constraints=())
    elif case == "name-pattern":
        with pytest.raises(ValueError, match="type variable name must match"):
            TypeVariable(name="T-U", constraints=())
    elif case == "container":
        with pytest.raises(TypeError, match="constraints must be an exact tuple"):
            TypeVariable(name="T", constraints=cast(Any, []))
    elif case == "member":
        with pytest.raises(TypeError, match="exact TypeConstraint members"):
            TypeVariable(name="T", constraints=cast(Any, ("numeric",)))
    elif case == "duplicate":
        with pytest.raises(ValueError, match="constraints must be unique"):
            TypeVariable(
                name="T",
                constraints=(TypeConstraint.SCALAR, TypeConstraint.SCALAR),
            )
    elif case == "frozen":
        value = TypeVariable(name="T", constraints=())
        with pytest.raises(FrozenInstanceError):
            setattr(value, "name", "U")
    else:
        value = TypeVariable(name="T", constraints=(TypeConstraint.NUMERIC,))
        assert hash(value)
        assert repr(value).startswith("TypeVariable(name='T'")


@pytest.mark.parametrize(
    ("label", "logical_type", "constraint", "expected"),
    _MATRIX_CASES,
)
def test_complete_type_by_constraint_truth_matrix_is_exact(
    label: str,
    logical_type: LogicalTypeIdentity | None,
    constraint: TypeConstraint,
    expected: bool,
) -> None:
    assert label
    assert supports_constraint(logical_type, constraint) is expected


@pytest.mark.parametrize(
    "case",
    (
        "alias",
        "unknown",
        "DateTime",
        "Time",
        "Interval",
        "Money",
        "Currency",
        "Null",
        "decimal",
    ),
)
def test_alias_unknown_deferred_and_decimal_precision_boundaries_are_exact(
    case: str,
) -> None:
    if case == "alias":
        with pytest.raises(ValueError, match="BUILTIN, ENUM, or SHAPE"):
            LogicalTypeIdentity(name="Alias", kind=TypeKind.TYPE_ALIAS)
    elif case == "unknown":
        with pytest.raises(ValueError, match="BUILTIN, ENUM, or SHAPE"):
            LogicalTypeIdentity(name="Unknown", kind=TypeKind.UNKNOWN)
    elif case == "decimal":
        value = LogicalTypeIdentity(name="Decimal", kind=TypeKind.BUILTIN)
        assert tuple(field.name for field in fields(value)) == ("name", "kind")
        assert not hasattr(value, "precision")
        assert not hasattr(value, "scale")
    else:
        with pytest.raises(ValueError, match="not in the exact catalog"):
            LogicalTypeIdentity(name=case, kind=TypeKind.BUILTIN)


@pytest.mark.parametrize(
    "case",
    (
        "concrete",
        "variable",
        "equality",
        "concrete-member",
        "variable-type",
        "variable-pattern",
        "frozen",
        "shape",
    ),
)
def test_concrete_and_variable_type_expression_shapes_are_exact(case: str) -> None:
    if case == "concrete":
        assert ConcreteTypeExpression(logical_type=INT).logical_type == INT
    elif case == "variable":
        assert VariableTypeExpression(name="T").name == "T"
    elif case == "equality":
        assert ConcreteTypeExpression(logical_type=INT) == ConcreteTypeExpression(
            logical_type=INT
        )
        assert hash(VariableTypeExpression(name="T"))
    elif case == "concrete-member":
        with pytest.raises(TypeError, match="requires an exact logical type"):
            ConcreteTypeExpression(logical_type=cast(Any, "Int"))
    elif case == "variable-type":
        with pytest.raises(TypeError, match="reference name must be an exact str"):
            VariableTypeExpression(name=cast(Any, 1))
    elif case == "variable-pattern":
        with pytest.raises(ValueError, match="reference name must match"):
            VariableTypeExpression(name="T-U")
    elif case == "frozen":
        value = ConcreteTypeExpression(logical_type=INT)
        with pytest.raises(FrozenInstanceError):
            setattr(value, "logical_type", FLOAT)
    else:
        assert tuple(field.name for field in fields(ConcreteTypeExpression)) == (
            "logical_type",
        )
        assert tuple(field.name for field in fields(VariableTypeExpression)) == (
            "name",
        )


@pytest.mark.parametrize(
    "case",
    (
        "required",
        "optional-none",
        "optional-marker",
        "negative",
        "bool-position",
        "position-type",
        "expression",
        "optional-type",
        "default-type",
        "default-required",
    ),
)
def test_parameter_position_optional_and_default_contract_is_exact(case: str) -> None:
    expression = ConcreteTypeExpression(logical_type=INT)
    if case == "required":
        value = SignatureParameter(position=0, type_expression=expression)
        assert (value.optional, value.default) == (False, None)
    elif case == "optional-none":
        value = SignatureParameter(
            position=0, type_expression=expression, optional=True
        )
        assert (value.optional, value.default) == (True, None)
    elif case == "optional-marker":
        value = SignatureParameter(
            position=0,
            type_expression=expression,
            optional=True,
            default=ParameterDefault.OMITTED,
        )
        assert value.default is ParameterDefault.OMITTED
    elif case == "negative":
        with pytest.raises(ValueError, match="position must be nonnegative"):
            SignatureParameter(position=-1, type_expression=expression)
    elif case == "bool-position":
        with pytest.raises(TypeError, match="position must be an exact int"):
            SignatureParameter(position=cast(Any, True), type_expression=expression)
    elif case == "position-type":
        with pytest.raises(TypeError, match="position must be an exact int"):
            SignatureParameter(position=cast(Any, "0"), type_expression=expression)
    elif case == "expression":
        with pytest.raises(TypeError, match="requires an exact type expression"):
            SignatureParameter(position=0, type_expression=cast(Any, INT))
    elif case == "optional-type":
        with pytest.raises(TypeError, match="optional must be an exact bool"):
            SignatureParameter(
                position=0,
                type_expression=expression,
                optional=cast(Any, 1),
            )
    elif case == "default-type":
        with pytest.raises(TypeError, match="exact ParameterDefault or None"):
            SignatureParameter(
                position=0,
                type_expression=expression,
                optional=True,
                default=cast(Any, "omitted"),
            )
    else:
        with pytest.raises(ValueError, match="default requires optional=True"):
            SignatureParameter(
                position=0,
                type_expression=expression,
                default=ParameterDefault.OMITTED,
            )


@pytest.mark.parametrize(
    "case",
    (
        "zero",
        "optional-only",
        "containers",
        "member",
        "duplicate",
        "positions",
        "optional-order",
        "undeclared-parameter",
        "undeclared-result",
        "unused-result-only",
    ),
)
def test_generic_signature_constructor_and_reference_invariants_are_exact(
    case: str,
) -> None:
    concrete = ConcreteTypeExpression(logical_type=INT)
    variable = TypeVariable(name="T", constraints=())
    reference = VariableTypeExpression(name="T")
    if case == "zero":
        value = GenericSignature(type_variables=(), parameters=(), result=concrete)
        assert value.parameters == ()
    elif case == "optional-only":
        value = GenericSignature(
            type_variables=(variable,),
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=reference,
                    optional=True,
                ),
            ),
            result=reference,
        )
        assert value.type_variables == (variable,)
    elif case == "containers":
        with pytest.raises(TypeError, match="type_variables must be an exact tuple"):
            GenericSignature(
                type_variables=cast(Any, []),
                parameters=(),
                result=concrete,
            )
        with pytest.raises(TypeError, match="parameters must be an exact tuple"):
            GenericSignature(
                type_variables=(),
                parameters=cast(Any, []),
                result=concrete,
            )
    elif case == "member":
        with pytest.raises(TypeError, match="exact TypeVariable members"):
            GenericSignature(
                type_variables=cast(Any, ("T",)),
                parameters=(),
                result=concrete,
            )
    elif case == "duplicate":
        with pytest.raises(ValueError, match="names must be unique"):
            GenericSignature(
                type_variables=(variable, variable),
                parameters=(SignatureParameter(position=0, type_expression=reference),),
                result=reference,
            )
    elif case == "positions":
        with pytest.raises(ValueError, match="positions must be continuous"):
            GenericSignature(
                type_variables=(),
                parameters=(SignatureParameter(position=1, type_expression=concrete),),
                result=concrete,
            )
    elif case == "optional-order":
        with pytest.raises(ValueError, match="trailing suffix"):
            GenericSignature(
                type_variables=(),
                parameters=(
                    SignatureParameter(
                        position=0,
                        type_expression=concrete,
                        optional=True,
                    ),
                    SignatureParameter(position=1, type_expression=concrete),
                ),
                result=concrete,
            )
    elif case == "undeclared-parameter":
        with pytest.raises(ValueError, match="reference declared variables"):
            GenericSignature(
                type_variables=(),
                parameters=(SignatureParameter(position=0, type_expression=reference),),
                result=concrete,
            )
    elif case == "undeclared-result":
        with pytest.raises(ValueError, match="reference declared variables"):
            GenericSignature(type_variables=(), parameters=(), result=reference)
    else:
        with pytest.raises(ValueError, match="must appear in a parameter"):
            GenericSignature(
                type_variables=(variable,),
                parameters=(),
                result=reference,
            )


@pytest.mark.parametrize(
    "case",
    (
        "one",
        "enum",
        "repeated",
        "repeated-mismatch",
        "arguments-container",
        "signature-member",
    ),
)
def test_unconstrained_and_repeated_variable_binding_is_exact(case: str) -> None:
    if case == "one":
        result = bind_signature(_variable_signature(), (INT,))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).bindings == (
            TypeVariableBinding(
                variable_name="T",
                logical_type=INT,
                first_parameter_position=0,
            ),
        )
    elif case == "enum":
        enum_type = LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM)
        result = bind_signature(_variable_signature(), (enum_type,))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).result_type == enum_type
    elif case == "repeated":
        result = bind_signature(_variable_signature(repeated=True), (INT, INT))
        assert type(result) is SignatureMatch
        assert len(cast(SignatureMatch, result).bindings) == 1
    elif case == "repeated-mismatch":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature(repeated=True), (INT, FLOAT)),
            RepeatedVariableMismatch,
        )
        assert cast(RepeatedVariableMismatch, mismatch).parameter_position == 1
    elif case == "arguments-container":
        with pytest.raises(TypeError, match="arguments must be an exact tuple"):
            bind_signature(_variable_signature(), cast(Any, [INT]))
    else:
        with pytest.raises(
            TypeError, match="signature must be an exact GenericSignature"
        ):
            bind_signature(cast(Any, "signature"), (INT,))


@pytest.mark.parametrize(
    "case",
    ("concrete", "concrete-mismatch", "mixed", "independent", "zero", "ordered"),
)
def test_concrete_mixed_and_independent_variable_binding_is_exact(case: str) -> None:
    if case == "concrete":
        result = bind_signature(_concrete_signature((INT,), TEXT), (INT,))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).result_type == TEXT
    elif case == "concrete-mismatch":
        mismatch = _assert_unsupported(
            bind_signature(_concrete_signature((INT,), TEXT), (FLOAT,)),
            ConcreteTypeMismatch,
        )
        assert cast(ConcreteTypeMismatch, mismatch).expected == INT
    elif case == "mixed":
        variable = TypeVariable(name="T", constraints=())
        signature = GenericSignature(
            type_variables=(variable,),
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=ConcreteTypeExpression(logical_type=TEXT),
                ),
                SignatureParameter(
                    position=1,
                    type_expression=VariableTypeExpression(name="T"),
                ),
            ),
            result=VariableTypeExpression(name="T"),
        )
        result = bind_signature(signature, (TEXT, INT))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).result_type == INT
    elif case == "independent":
        variables = (
            TypeVariable(name="U", constraints=()),
            TypeVariable(name="T", constraints=()),
        )
        signature = GenericSignature(
            type_variables=variables,
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=VariableTypeExpression(name="T"),
                ),
                SignatureParameter(
                    position=1,
                    type_expression=VariableTypeExpression(name="U"),
                ),
            ),
            result=VariableTypeExpression(name="U"),
        )
        result = cast(SignatureMatch, bind_signature(signature, (INT, TEXT)))
        assert tuple(binding.variable_name for binding in result.bindings) == ("T", "U")
        assert result.result_type == TEXT
    elif case == "zero":
        result = bind_signature(_concrete_signature((), BOOL), ())
        assert result == SignatureMatch(
            bindings=(),
            result_type=BOOL,
            constraint_evidence=(),
            omitted_positions=(),
        )
    else:
        signature = _concrete_signature((INT, TEXT), BOOL)
        mismatch = cast(
            ConcreteTypeMismatch,
            _assert_unsupported(
                bind_signature(signature, (INT, UUID)),
                ConcreteTypeMismatch,
            ),
        )
        assert mismatch.parameter_position == 1


_IDENTITY_MISMATCH_CASES = (
    (INT, FLOAT),
    (FLOAT, DECIMAL),
    (TEXT, UUID),
    (DATE, TEXT),
    (BOOL, INT),
    (
        LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM),
        LogicalTypeIdentity(name="orderState", kind=TypeKind.ENUM),
    ),
    (
        LogicalTypeIdentity(name="Entity", kind=TypeKind.ENUM),
        LogicalTypeIdentity(name="Entity", kind=TypeKind.SHAPE),
    ),
    (
        LogicalTypeIdentity(name="OrderRow", kind=TypeKind.SHAPE),
        LogicalTypeIdentity(name="orderRow", kind=TypeKind.SHAPE),
    ),
)


@pytest.mark.parametrize(("expected", "actual"), _IDENTITY_MISMATCH_CASES)
def test_exact_logical_identity_binding_has_no_case_or_kind_coercion(
    expected: LogicalTypeIdentity,
    actual: LogicalTypeIdentity,
) -> None:
    mismatch = _assert_unsupported(
        bind_signature(_concrete_signature((expected,), BOOL), (actual,)),
        ConcreteTypeMismatch,
    )
    assert cast(ConcreteTypeMismatch, mismatch).actual == actual


@pytest.mark.parametrize(
    "case",
    (
        "omitted",
        "default",
        "supplied",
        "unbound",
        "optional-result",
        "two-omitted",
        "one-of-two",
    ),
)
def test_optional_trailing_parameter_binding_and_omission_is_exact(case: str) -> None:
    if case == "omitted":
        signature = _concrete_signature((INT, TEXT), BOOL, optional_from=1)
        result = cast(SignatureMatch, bind_signature(signature, (INT,)))
        assert result.omitted_positions == (1,)
    elif case == "default":
        signature = GenericSignature(
            type_variables=(),
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=ConcreteTypeExpression(logical_type=INT),
                    optional=True,
                    default=ParameterDefault.OMITTED,
                ),
            ),
            result=ConcreteTypeExpression(logical_type=BOOL),
        )
        result = cast(SignatureMatch, bind_signature(signature, ()))
        assert result.omitted_positions == (0,)
    elif case == "supplied":
        signature = _concrete_signature((INT,), BOOL, optional_from=0)
        assert (
            cast(SignatureMatch, bind_signature(signature, (INT,))).omitted_positions
            == ()
        )
    elif case == "unbound":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature(optional=True), ()),
            UnboundResult,
        )
        assert cast(UnboundResult, mismatch).variable_name == "T"
    elif case == "optional-result":
        result = bind_signature(_variable_signature(optional=True), (TEXT,))
        assert cast(SignatureMatch, result).result_type == TEXT
    elif case == "two-omitted":
        signature = _concrete_signature((INT, TEXT), BOOL, optional_from=0)
        assert cast(
            SignatureMatch, bind_signature(signature, ())
        ).omitted_positions == (
            0,
            1,
        )
    else:
        signature = _concrete_signature((INT, TEXT, UUID), BOOL, optional_from=1)
        assert cast(
            SignatureMatch, bind_signature(signature, (INT, TEXT))
        ).omitted_positions == (2,)


_ARITY_CASES = (
    (_concrete_signature((INT,), BOOL), (), (1, 1, 0)),
    (_concrete_signature((INT,), BOOL), (INT, INT), (1, 1, 2)),
    (_concrete_signature((INT, TEXT, UUID), BOOL, optional_from=2), (INT,), (2, 3, 1)),
    (
        _concrete_signature((INT, TEXT, UUID), BOOL, optional_from=2),
        (INT, TEXT, UUID, BOOL),
        (2, 3, 4),
    ),
)


@pytest.mark.parametrize(("signature", "arguments", "expected"), _ARITY_CASES)
def test_arity_mismatch_evidence_is_exact(
    signature: GenericSignature,
    arguments: tuple[LogicalTypeIdentity, ...],
    expected: tuple[int, int, int],
) -> None:
    mismatch = cast(
        ArityMismatch,
        _assert_unsupported(bind_signature(signature, arguments), ArityMismatch),
    )
    assert (mismatch.minimum, mismatch.maximum, mismatch.actual) == expected


@pytest.mark.parametrize(
    "case",
    (
        "member-type",
        "unresolved",
        "concrete-precedence",
        "repeated-precedence",
        "constraint",
        "constraint-order",
        "unbound",
        "structured",
    ),
)
def test_binding_failures_are_structured_ordered_and_fail_closed(case: str) -> None:
    if case == "member-type":
        with pytest.raises(TypeError, match="exact LogicalTypeIdentity or None"):
            bind_signature(_variable_signature(), cast(Any, ("Int",)))
    elif case == "unresolved":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature(repeated=True), (None, FLOAT)),
            UnresolvedArgument,
        )
        assert cast(UnresolvedArgument, mismatch).parameter_position == 0
    elif case == "concrete-precedence":
        signature = _concrete_signature((INT, TEXT), BOOL)
        mismatch = _assert_unsupported(
            bind_signature(signature, (FLOAT, None)),
            ConcreteTypeMismatch,
        )
        assert cast(ConcreteTypeMismatch, mismatch).parameter_position == 0
    elif case == "repeated-precedence":
        signature = _variable_signature(
            (TypeConstraint.NUMERIC,),
            repeated=True,
        )
        mismatch = _assert_unsupported(
            bind_signature(signature, (TEXT, UUID)),
            RepeatedVariableMismatch,
        )
        assert cast(RepeatedVariableMismatch, mismatch).parameter_position == 1
    elif case == "constraint":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature((TypeConstraint.NUMERIC,)), (TEXT,)),
            ConstraintMismatch,
        )
        assert cast(ConstraintMismatch, mismatch).constraint is TypeConstraint.NUMERIC
    elif case == "constraint-order":
        signature = _variable_signature(
            (TypeConstraint.ORDERABLE, TypeConstraint.NUMERIC)
        )
        mismatch = cast(
            ConstraintMismatch,
            _assert_unsupported(bind_signature(signature, (TEXT,)), ConstraintMismatch),
        )
        assert mismatch.constraint is TypeConstraint.ORDERABLE
    elif case == "unbound":
        assert (
            type(
                _assert_unsupported(
                    bind_signature(_variable_signature(optional=True), ()),
                    UnboundResult,
                )
            )
            is UnboundResult
        )
    else:
        result = bind_signature(_concrete_signature((INT,), BOOL), (FLOAT,))
        assert type(result) is SignatureUnsupported
        assert type(result.mismatch) is ConcreteTypeMismatch


_CONSTRAINT_ORDER_CASES = (
    (
        INT,
        (
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
            TypeConstraint.ORDERABLE,
            TypeConstraint.NUMERIC,
        ),
    ),
    (
        DATE,
        (
            TypeConstraint.ORDERABLE,
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
        ),
    ),
    (BOOL, (TypeConstraint.COMPARABLE, TypeConstraint.SCALAR)),
    (DECIMAL, (TypeConstraint.NUMERIC, TypeConstraint.ORDERABLE)),
)


@pytest.mark.parametrize(("logical_type", "constraints"), _CONSTRAINT_ORDER_CASES)
def test_multiple_constraint_evidence_uses_declaration_order(
    logical_type: LogicalTypeIdentity,
    constraints: tuple[TypeConstraint, ...],
) -> None:
    result = cast(
        SignatureMatch,
        bind_signature(_variable_signature(constraints), (logical_type,)),
    )
    assert (
        tuple(evidence.constraint for evidence in result.constraint_evidence)
        == constraints
    )
    assert all(evidence.supported for evidence in result.constraint_evidence)
    assert all(
        evidence.parameter_position == 0 for evidence in result.constraint_evidence
    )


@pytest.mark.parametrize("case", ("concrete", "variable", "second", "unbound"))
def test_variable_and_concrete_result_resolution_is_exact(case: str) -> None:
    if case == "concrete":
        result = bind_signature(_variable_signature(result=BOOL), (INT,))
        assert cast(SignatureMatch, result).result_type == BOOL
    elif case == "variable":
        result = bind_signature(_variable_signature(), (DECIMAL,))
        assert cast(SignatureMatch, result).result_type == DECIMAL
    elif case == "second":
        variables = (
            TypeVariable(name="T", constraints=()),
            TypeVariable(name="U", constraints=()),
        )
        signature = GenericSignature(
            type_variables=variables,
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=VariableTypeExpression(name="T"),
                ),
                SignatureParameter(
                    position=1,
                    type_expression=VariableTypeExpression(name="U"),
                ),
            ),
            result=VariableTypeExpression(name="U"),
        )
        assert (
            cast(SignatureMatch, bind_signature(signature, (INT, TEXT))).result_type
            == TEXT
        )
    else:
        assert (
            type(
                _assert_unsupported(
                    bind_signature(_variable_signature(optional=True), ()),
                    UnboundResult,
                )
            )
            is UnboundResult
        )


def test_binding_results_are_immutable_hashable_and_repeatable() -> None:
    signature = _variable_signature(
        (TypeConstraint.SCALAR, TypeConstraint.COMPARABLE),
        repeated=True,
    )
    first = bind_signature(signature, (INT, INT))
    second = bind_signature(signature, (INT, INT))
    assert first == second
    assert hash(first) == hash(second)
    assert type(first) is SignatureMatch
    with pytest.raises(FrozenInstanceError):
        setattr(first, "result_type", FLOAT)
    mismatch = bind_signature(signature, (INT, FLOAT))
    assert hash(mismatch)
    assert mismatch == bind_signature(signature, (INT, FLOAT))


@pytest.mark.parametrize("case", ("empty", "one", "order", "duplicate", "invalid"))
def test_overload_collection_preserves_order_and_duplicate_rows(case: str) -> None:
    int_signature = _concrete_signature((INT,), INT)
    text_signature = _concrete_signature((TEXT,), TEXT)
    if case == "empty":
        assert OverloadSet(signatures=()).signatures == ()
    elif case == "one":
        assert OverloadSet(signatures=(int_signature,)).signatures == (int_signature,)
    elif case == "order":
        value = OverloadSet(signatures=(text_signature, int_signature))
        assert value.signatures == (text_signature, int_signature)
    elif case == "duplicate":
        value = OverloadSet(signatures=(int_signature, int_signature))
        assert value.signatures == (int_signature, int_signature)
    else:
        with pytest.raises(TypeError, match="signatures must be an exact tuple"):
            OverloadSet(signatures=cast(Any, [int_signature]))
        with pytest.raises(TypeError, match="exact GenericSignature members"):
            OverloadSet(signatures=cast(Any, ("signature",)))


@pytest.mark.parametrize("case", ("empty", "match", "unsupported", "mixed"))
def test_overload_selection_match_and_unsupported_outcomes_are_exact(
    case: str,
) -> None:
    int_signature = _concrete_signature((INT,), INT)
    text_signature = _concrete_signature((TEXT,), TEXT)
    if case == "empty":
        selection = select_overload(OverloadSet(signatures=()), (INT,))
        assert selection == OverloadSelection(
            outcome=OverloadOutcome.UNSUPPORTED,
            evaluations=(),
        )
    elif case == "match":
        selection = select_overload(
            OverloadSet(signatures=(int_signature,)),
            (INT,),
        )
        assert selection.outcome is OverloadOutcome.MATCH
        assert type(selection.evaluations[0].result) is SignatureMatch
    elif case == "unsupported":
        selection = select_overload(
            OverloadSet(signatures=(text_signature,)),
            (INT,),
        )
        assert selection.outcome is OverloadOutcome.UNSUPPORTED
        assert type(selection.evaluations[0].result) is SignatureUnsupported
    else:
        selection = select_overload(
            OverloadSet(signatures=(text_signature, int_signature)),
            (INT,),
        )
        assert selection.outcome is OverloadOutcome.MATCH
        assert tuple(type(item.result) for item in selection.evaluations) == (
            SignatureUnsupported,
            SignatureMatch,
        )


@pytest.mark.parametrize(
    "case", ("duplicate", "generic", "indices", "three", "evidence")
)
def test_overload_ambiguity_preserves_every_matching_candidate_in_order(
    case: str,
) -> None:
    int_signature = _concrete_signature((INT,), INT)
    generic_signature = _variable_signature()
    mismatch_signature = _concrete_signature((TEXT,), TEXT)
    if case == "duplicate":
        signatures = (int_signature, int_signature)
    elif case == "generic":
        signatures = (generic_signature, int_signature)
    elif case == "indices":
        signatures = (int_signature, mismatch_signature, generic_signature)
    elif case == "three":
        signatures = (int_signature, generic_signature, int_signature)
    else:
        signatures = (mismatch_signature, generic_signature, int_signature)
    selection = select_overload(OverloadSet(signatures=signatures), (INT,))
    assert selection.outcome is OverloadOutcome.AMBIGUOUS
    assert tuple(item.index for item in selection.evaluations) == tuple(
        range(len(signatures))
    )
    assert (
        sum(type(item.result) is SignatureMatch for item in selection.evaluations) >= 2
    )


@pytest.mark.parametrize("case", ("specificity", "result", "reverse", "three"))
def test_overload_selection_has_no_first_match_or_tiebreaker(case: str) -> None:
    generic = _variable_signature()
    concrete_int = _concrete_signature((INT,), INT)
    concrete_bool = _concrete_signature((INT,), BOOL)
    if case == "specificity":
        signatures = (generic, concrete_int)
    elif case == "result":
        signatures = (concrete_int, concrete_bool)
    elif case == "reverse":
        signatures = (concrete_int, generic)
    else:
        signatures = (concrete_int, _concrete_signature((TEXT,), TEXT), generic)
    selection = select_overload(OverloadSet(signatures=signatures), (INT,))
    assert selection.outcome is OverloadOutcome.AMBIGUOUS
    assert tuple(item.index for item in selection.evaluations) == tuple(
        range(len(signatures))
    )


def test_phase52_capability_facts_are_evidence_not_compatibility_authority() -> None:
    source = SOURCE_PATH.read_text()
    for forbidden in (
        "capability_facts",
        "capability_lookup",
        "capability_inventory",
        "capability_signatures",
        "capability_contexts",
        "capability_aggregates",
        "Found",
        "Absent",
        "Conflict",
    ):
        assert forbidden not in source


def test_current_semantic_analyzer_and_window_paths_do_not_import_generic_compatibility() -> (
    None
):
    for relative in (
        "src/pietto/semantic/analyzer.py",
        "src/pietto/semantic/catalog.py",
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/aggregates.py",
        "src/pietto/semantic/type_aliases.py",
        "src/pietto/_window_identity.py",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
    ):
        assert "generic_compatibility" not in (REPO_ROOT / relative).read_text()
    window_analysis = (REPO_ROOT / "src/pietto/semantic/window_analysis.py").read_text()
    assert "pietto.semantic.generic_compatibility import" in window_analysis
    assert "_RANKING_SIGNATURE = GenericSignature(" in window_analysis
    assert "_ROW_NUMBER_SIGNATURE = _RANKING_SIGNATURE" in window_analysis
    assert "bind_signature(signature, signature_arguments)" in window_analysis
    for identity in ("row_number", "rank", "dense_rank"):
        assert f'name="{identity}"' in window_analysis
    assert "PIE-S2103" in (REPO_ROOT / "src/pietto/semantic/expressions.py").read_text()


def test_nullability_phase5_and_phase64_exclusions_are_exact() -> None:
    source = SOURCE_PATH.read_text()
    assert "EffectiveNullability" not in source
    assert "DecimalPrecisionScale" not in source
    assert all(
        "nullability" not in field.name
        for carrier in (
            LogicalTypeIdentity,
            TypeVariable,
            SignatureParameter,
            GenericSignature,
            SignatureMatch,
        )
        for field in fields(carrier)
    )


# Phase 53 Slice 13 reader migration.
