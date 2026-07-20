"""Private exact generic-signature compatibility foundation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from pietto.semantic.model import TypeKind

__all__: tuple[str, ...] = ()

_IDENTIFIER_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"
_BUILTIN_NAMES = (
    "Any",
    "Bool",
    "Bytes",
    "Date",
    "Decimal",
    "Float",
    "Int",
    "Json",
    "Text",
    "Timestamp",
    "UUID",
)


class TypeConstraint(StrEnum):
    """Exact private generic-constraint tags."""

    SCALAR = "scalar"
    COMPARABLE = "comparable"
    ORDERABLE = "orderable"
    NUMERIC = "numeric"


class ParameterDefault(StrEnum):
    """Marker for an optional omitted signature argument."""

    OMITTED = "omitted"


class OverloadOutcome(StrEnum):
    """Deterministic exact-overload selection outcomes."""

    MATCH = "match"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"


def _require_identifier(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field_name} must be an exact str")
    if re.fullmatch(_IDENTIFIER_PATTERN, value, flags=re.ASCII) is None:
        raise ValueError(f"{field_name} must match {_IDENTIFIER_PATTERN}")
    return value


def _require_nonnegative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field_name} must be an exact int")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class LogicalTypeIdentity:
    """A source-independent exact logical-type identity."""

    name: str
    kind: TypeKind

    def __post_init__(self) -> None:
        name = _require_identifier(self.name, "logical type name")
        if type(self.kind) is not TypeKind:
            raise TypeError("logical type kind must be an exact TypeKind")
        if self.kind not in {TypeKind.BUILTIN, TypeKind.ENUM, TypeKind.SHAPE}:
            raise ValueError("logical type kind must be BUILTIN, ENUM, or SHAPE")
        if self.kind is TypeKind.BUILTIN and name not in _BUILTIN_NAMES:
            raise ValueError("builtin logical type name is not in the exact catalog")


_BUILTIN_CONSTRAINT_MATRIX: tuple[tuple[str, tuple[TypeConstraint, ...]], ...] = (
    ("Any", (TypeConstraint.SCALAR,)),
    ("Bool", (TypeConstraint.SCALAR, TypeConstraint.COMPARABLE)),
    ("Bytes", (TypeConstraint.SCALAR,)),
    (
        "Date",
        (
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
            TypeConstraint.ORDERABLE,
        ),
    ),
    (
        "Decimal",
        (
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
            TypeConstraint.ORDERABLE,
            TypeConstraint.NUMERIC,
        ),
    ),
    (
        "Float",
        (
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
            TypeConstraint.ORDERABLE,
            TypeConstraint.NUMERIC,
        ),
    ),
    (
        "Int",
        (
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
            TypeConstraint.ORDERABLE,
            TypeConstraint.NUMERIC,
        ),
    ),
    ("Json", (TypeConstraint.SCALAR,)),
    ("Text", (TypeConstraint.SCALAR, TypeConstraint.COMPARABLE)),
    (
        "Timestamp",
        (
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
            TypeConstraint.ORDERABLE,
        ),
    ),
    ("UUID", (TypeConstraint.SCALAR, TypeConstraint.COMPARABLE)),
)


def supports_constraint(
    logical_type: LogicalTypeIdentity | None,
    constraint: TypeConstraint,
) -> bool:
    """Return one explicit matrix result without inferred hierarchy."""

    if logical_type is not None and type(logical_type) is not LogicalTypeIdentity:
        raise TypeError("logical_type must be an exact LogicalTypeIdentity or None")
    if type(constraint) is not TypeConstraint:
        raise TypeError("constraint must be an exact TypeConstraint")
    if logical_type is None or logical_type.kind is not TypeKind.BUILTIN:
        return False
    for name, supported_constraints in _BUILTIN_CONSTRAINT_MATRIX:
        if logical_type.name == name:
            return constraint in supported_constraints
    return False


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeVariable:
    """One declared exact type variable and its ordered constraints."""

    name: str
    constraints: tuple[TypeConstraint, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.name, "type variable name")
        if type(self.constraints) is not tuple:
            raise TypeError("type variable constraints must be an exact tuple")
        if any(
            type(constraint) is not TypeConstraint for constraint in self.constraints
        ):
            raise TypeError(
                "type variable constraints require exact TypeConstraint members"
            )
        if len(set(self.constraints)) != len(self.constraints):
            raise ValueError("type variable constraints must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class ConcreteTypeExpression:
    """A concrete exact logical-type expression."""

    logical_type: LogicalTypeIdentity

    def __post_init__(self) -> None:
        if type(self.logical_type) is not LogicalTypeIdentity:
            raise TypeError("concrete type expression requires an exact logical type")


@dataclass(frozen=True, slots=True, kw_only=True)
class VariableTypeExpression:
    """A reference to a declared exact type variable."""

    name: str

    def __post_init__(self) -> None:
        _require_identifier(self.name, "type variable reference name")


type TypeExpression = ConcreteTypeExpression | VariableTypeExpression


def _require_type_expression(value: object, field_name: str) -> None:
    if type(value) not in {ConcreteTypeExpression, VariableTypeExpression}:
        raise TypeError(f"{field_name} requires an exact type expression")


@dataclass(frozen=True, slots=True, kw_only=True)
class SignatureParameter:
    """One source-ordered exact signature parameter."""

    position: int
    type_expression: TypeExpression
    optional: bool = False
    default: ParameterDefault | None = None

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.position, "parameter position")
        _require_type_expression(self.type_expression, "parameter type_expression")
        if type(self.optional) is not bool:
            raise TypeError("parameter optional must be an exact bool")
        if self.default is not None and type(self.default) is not ParameterDefault:
            raise TypeError(
                "parameter default must be an exact ParameterDefault or None"
            )
        if self.default is not None and not self.optional:
            raise ValueError("parameter default requires optional=True")


@dataclass(frozen=True, slots=True, kw_only=True)
class GenericSignature:
    """An ordered exact generic signature without callable identity."""

    type_variables: tuple[TypeVariable, ...]
    parameters: tuple[SignatureParameter, ...]
    result: TypeExpression

    def __post_init__(self) -> None:
        if type(self.type_variables) is not tuple:
            raise TypeError("signature type_variables must be an exact tuple")
        if any(type(variable) is not TypeVariable for variable in self.type_variables):
            raise TypeError(
                "signature type_variables require exact TypeVariable members"
            )
        if type(self.parameters) is not tuple:
            raise TypeError("signature parameters must be an exact tuple")
        if any(
            type(parameter) is not SignatureParameter for parameter in self.parameters
        ):
            raise TypeError(
                "signature parameters require exact SignatureParameter members"
            )
        _require_type_expression(self.result, "signature result")

        variable_names = tuple(variable.name for variable in self.type_variables)
        if len(set(variable_names)) != len(variable_names):
            raise ValueError("signature type variable names must be unique")

        optional_started = False
        parameter_references: set[str] = set()
        for expected_position, parameter in enumerate(self.parameters):
            if parameter.position != expected_position:
                raise ValueError(
                    "signature parameter positions must be continuous from zero"
                )
            if parameter.optional:
                optional_started = True
            elif optional_started:
                raise ValueError(
                    "signature optional parameters must form a trailing suffix"
                )
            if type(parameter.type_expression) is VariableTypeExpression:
                parameter_references.add(parameter.type_expression.name)

        declared_names = set(variable_names)
        result_references: set[str] = set()
        if type(self.result) is VariableTypeExpression:
            result_references.add(self.result.name)
        if not parameter_references.union(result_references).issubset(declared_names):
            raise ValueError(
                "signature type expressions must reference declared variables"
            )
        if parameter_references != declared_names:
            raise ValueError("each signature type variable must appear in a parameter")


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeVariableBinding:
    """The exact first binding of one type variable."""

    variable_name: str
    logical_type: LogicalTypeIdentity
    first_parameter_position: int

    def __post_init__(self) -> None:
        _require_identifier(self.variable_name, "binding variable_name")
        if type(self.logical_type) is not LogicalTypeIdentity:
            raise TypeError("binding logical_type must be exact")
        _require_nonnegative_int(
            self.first_parameter_position,
            "binding first_parameter_position",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstraintEvidence:
    """One ordered constraint check for a bound type variable."""

    variable_name: str
    logical_type: LogicalTypeIdentity
    constraint: TypeConstraint
    parameter_position: int
    supported: bool

    def __post_init__(self) -> None:
        _require_identifier(self.variable_name, "constraint evidence variable_name")
        if type(self.logical_type) is not LogicalTypeIdentity:
            raise TypeError("constraint evidence logical_type must be exact")
        if type(self.constraint) is not TypeConstraint:
            raise TypeError("constraint evidence constraint must be exact")
        _require_nonnegative_int(
            self.parameter_position,
            "constraint evidence parameter_position",
        )
        if type(self.supported) is not bool:
            raise TypeError("constraint evidence supported must be an exact bool")


@dataclass(frozen=True, slots=True, kw_only=True)
class ArityMismatch:
    """A supplied-argument count outside the exact signature range."""

    minimum: int
    maximum: int
    actual: int

    def __post_init__(self) -> None:
        minimum = _require_nonnegative_int(self.minimum, "arity minimum")
        maximum = _require_nonnegative_int(self.maximum, "arity maximum")
        actual = _require_nonnegative_int(self.actual, "arity actual")
        if minimum > maximum:
            raise ValueError("arity minimum cannot exceed maximum")
        if minimum <= actual <= maximum:
            raise ValueError("arity mismatch actual must be outside the accepted range")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnresolvedArgument:
    """An unresolved argument at one supplied position."""

    parameter_position: int

    def __post_init__(self) -> None:
        _require_nonnegative_int(
            self.parameter_position, "unresolved parameter_position"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConcreteTypeMismatch:
    """A concrete parameter exact-identity mismatch."""

    parameter_position: int
    expected: LogicalTypeIdentity
    actual: LogicalTypeIdentity

    def __post_init__(self) -> None:
        _require_nonnegative_int(
            self.parameter_position,
            "concrete mismatch parameter_position",
        )
        if type(self.expected) is not LogicalTypeIdentity:
            raise TypeError("concrete mismatch expected must be exact")
        if type(self.actual) is not LogicalTypeIdentity:
            raise TypeError("concrete mismatch actual must be exact")
        if self.expected == self.actual:
            raise ValueError("concrete mismatch identities must differ")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepeatedVariableMismatch:
    """A repeated type variable bound to a different exact identity."""

    parameter_position: int
    variable_name: str
    expected: LogicalTypeIdentity
    actual: LogicalTypeIdentity

    def __post_init__(self) -> None:
        _require_nonnegative_int(
            self.parameter_position,
            "repeated mismatch parameter_position",
        )
        _require_identifier(self.variable_name, "repeated mismatch variable_name")
        if type(self.expected) is not LogicalTypeIdentity:
            raise TypeError("repeated mismatch expected must be exact")
        if type(self.actual) is not LogicalTypeIdentity:
            raise TypeError("repeated mismatch actual must be exact")
        if self.expected == self.actual:
            raise ValueError("repeated mismatch identities must differ")


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstraintMismatch:
    """The first unsupported declared constraint for a binding."""

    parameter_position: int
    variable_name: str
    logical_type: LogicalTypeIdentity
    constraint: TypeConstraint

    def __post_init__(self) -> None:
        _require_nonnegative_int(
            self.parameter_position,
            "constraint mismatch parameter_position",
        )
        _require_identifier(self.variable_name, "constraint mismatch variable_name")
        if type(self.logical_type) is not LogicalTypeIdentity:
            raise TypeError("constraint mismatch logical_type must be exact")
        if type(self.constraint) is not TypeConstraint:
            raise TypeError("constraint mismatch constraint must be exact")
        if supports_constraint(self.logical_type, self.constraint):
            raise ValueError("constraint mismatch requires unsupported evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnboundResult:
    """A variable result without a supplied argument binding."""

    variable_name: str

    def __post_init__(self) -> None:
        _require_identifier(self.variable_name, "unbound result variable_name")


type SignatureMismatch = (
    ArityMismatch
    | UnresolvedArgument
    | ConcreteTypeMismatch
    | RepeatedVariableMismatch
    | ConstraintMismatch
    | UnboundResult
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SignatureMatch:
    """A successful exact signature binding and ordered evidence."""

    bindings: tuple[TypeVariableBinding, ...]
    result_type: LogicalTypeIdentity
    constraint_evidence: tuple[ConstraintEvidence, ...]
    omitted_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.bindings) is not tuple:
            raise TypeError("signature match bindings must be an exact tuple")
        if any(type(binding) is not TypeVariableBinding for binding in self.bindings):
            raise TypeError("signature match bindings require exact members")
        if len({binding.variable_name for binding in self.bindings}) != len(
            self.bindings
        ):
            raise ValueError("signature match bindings must have unique variables")
        if tuple(
            binding.first_parameter_position for binding in self.bindings
        ) != tuple(
            sorted(binding.first_parameter_position for binding in self.bindings)
        ):
            raise ValueError(
                "signature match bindings must preserve first-binding order"
            )
        if type(self.result_type) is not LogicalTypeIdentity:
            raise TypeError("signature match result_type must be exact")
        if type(self.constraint_evidence) is not tuple:
            raise TypeError(
                "signature match constraint_evidence must be an exact tuple"
            )
        if any(
            type(evidence) is not ConstraintEvidence
            for evidence in self.constraint_evidence
        ):
            raise TypeError("signature match constraint_evidence require exact members")
        if any(not evidence.supported for evidence in self.constraint_evidence):
            raise ValueError("signature match constraint evidence must be supported")
        if type(self.omitted_positions) is not tuple:
            raise TypeError("signature match omitted_positions must be an exact tuple")
        for position in self.omitted_positions:
            _require_nonnegative_int(position, "omitted position")
        if self.omitted_positions != tuple(sorted(set(self.omitted_positions))):
            raise ValueError(
                "signature match omitted_positions must be unique and ordered"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SignatureUnsupported:
    """A valid signature rejected by one structured mismatch."""

    mismatch: SignatureMismatch

    def __post_init__(self) -> None:
        if type(self.mismatch) not in {
            ArityMismatch,
            UnresolvedArgument,
            ConcreteTypeMismatch,
            RepeatedVariableMismatch,
            ConstraintMismatch,
            UnboundResult,
        }:
            raise TypeError("signature unsupported mismatch must be exact")


type SignatureBindingResult = SignatureMatch | SignatureUnsupported


@dataclass(frozen=True, slots=True, kw_only=True)
class OverloadSet:
    """An ordered duplicate-preserving collection of signatures."""

    signatures: tuple[GenericSignature, ...]

    def __post_init__(self) -> None:
        if type(self.signatures) is not tuple:
            raise TypeError("overload signatures must be an exact tuple")
        if any(
            type(signature) is not GenericSignature for signature in self.signatures
        ):
            raise TypeError(
                "overload signatures require exact GenericSignature members"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvaluation:
    """One source-ordered overload candidate evaluation."""

    index: int
    result: SignatureBindingResult

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.index, "candidate index")
        if type(self.result) not in {SignatureMatch, SignatureUnsupported}:
            raise TypeError("candidate result must be an exact binding result")


@dataclass(frozen=True, slots=True, kw_only=True)
class OverloadSelection:
    """A deterministic selection outcome with all candidate evidence."""

    outcome: OverloadOutcome
    evaluations: tuple[CandidateEvaluation, ...]

    def __post_init__(self) -> None:
        if type(self.outcome) is not OverloadOutcome:
            raise TypeError("selection outcome must be an exact OverloadOutcome")
        if type(self.evaluations) is not tuple:
            raise TypeError("selection evaluations must be an exact tuple")
        if any(
            type(evaluation) is not CandidateEvaluation
            for evaluation in self.evaluations
        ):
            raise TypeError(
                "selection evaluations require exact CandidateEvaluation members"
            )
        if tuple(evaluation.index for evaluation in self.evaluations) != tuple(
            range(len(self.evaluations))
        ):
            raise ValueError("selection candidate indices must be continuous from zero")
        match_count = sum(
            type(evaluation.result) is SignatureMatch for evaluation in self.evaluations
        )
        expected_outcome = (
            OverloadOutcome.UNSUPPORTED
            if match_count == 0
            else OverloadOutcome.MATCH
            if match_count == 1
            else OverloadOutcome.AMBIGUOUS
        )
        if self.outcome is not expected_outcome:
            raise ValueError("selection outcome must match candidate evidence")


def bind_signature(
    signature: GenericSignature,
    arguments: tuple[LogicalTypeIdentity | None, ...],
) -> SignatureBindingResult:
    """Bind exact logical identities to one signature without conversion."""

    if type(signature) is not GenericSignature:
        raise TypeError("signature must be an exact GenericSignature")
    if type(arguments) is not tuple:
        raise TypeError("arguments must be an exact tuple")
    if any(
        argument is not None and type(argument) is not LogicalTypeIdentity
        for argument in arguments
    ):
        raise TypeError("arguments require exact LogicalTypeIdentity or None members")

    minimum = sum(not parameter.optional for parameter in signature.parameters)
    maximum = len(signature.parameters)
    actual = len(arguments)
    if actual < minimum or actual > maximum:
        return SignatureUnsupported(
            mismatch=ArityMismatch(minimum=minimum, maximum=maximum, actual=actual)
        )

    bindings: list[TypeVariableBinding] = []
    bindings_by_name: dict[str, TypeVariableBinding] = {}
    for parameter, argument in zip(signature.parameters, arguments, strict=False):
        if argument is None:
            return SignatureUnsupported(
                mismatch=UnresolvedArgument(parameter_position=parameter.position)
            )
        expression = parameter.type_expression
        if type(expression) is ConcreteTypeExpression:
            if argument != expression.logical_type:
                return SignatureUnsupported(
                    mismatch=ConcreteTypeMismatch(
                        parameter_position=parameter.position,
                        expected=expression.logical_type,
                        actual=argument,
                    )
                )
            continue

        assert isinstance(expression, VariableTypeExpression)
        existing = bindings_by_name.get(expression.name)
        if existing is None:
            binding = TypeVariableBinding(
                variable_name=expression.name,
                logical_type=argument,
                first_parameter_position=parameter.position,
            )
            bindings.append(binding)
            bindings_by_name[expression.name] = binding
        elif argument != existing.logical_type:
            return SignatureUnsupported(
                mismatch=RepeatedVariableMismatch(
                    parameter_position=parameter.position,
                    variable_name=expression.name,
                    expected=existing.logical_type,
                    actual=argument,
                )
            )

    variables_by_name = {
        variable.name: variable for variable in signature.type_variables
    }
    constraint_evidence: list[ConstraintEvidence] = []
    for binding in bindings:
        variable = variables_by_name[binding.variable_name]
        for constraint in variable.constraints:
            supported = supports_constraint(binding.logical_type, constraint)
            if not supported:
                return SignatureUnsupported(
                    mismatch=ConstraintMismatch(
                        parameter_position=binding.first_parameter_position,
                        variable_name=binding.variable_name,
                        logical_type=binding.logical_type,
                        constraint=constraint,
                    )
                )
            constraint_evidence.append(
                ConstraintEvidence(
                    variable_name=binding.variable_name,
                    logical_type=binding.logical_type,
                    constraint=constraint,
                    parameter_position=binding.first_parameter_position,
                    supported=True,
                )
            )

    omitted_positions = tuple(range(actual, maximum))
    if type(signature.result) is ConcreteTypeExpression:
        result_type = signature.result.logical_type
    else:
        assert isinstance(signature.result, VariableTypeExpression)
        result_binding = bindings_by_name.get(signature.result.name)
        if result_binding is None:
            return SignatureUnsupported(
                mismatch=UnboundResult(variable_name=signature.result.name)
            )
        result_type = result_binding.logical_type

    return SignatureMatch(
        bindings=tuple(bindings),
        result_type=result_type,
        constraint_evidence=tuple(constraint_evidence),
        omitted_positions=omitted_positions,
    )


def select_overload(
    overloads: OverloadSet,
    arguments: tuple[LogicalTypeIdentity | None, ...],
) -> OverloadSelection:
    """Evaluate every overload and classify the exact ordered match count."""

    if type(overloads) is not OverloadSet:
        raise TypeError("overloads must be an exact OverloadSet")
    if type(arguments) is not tuple:
        raise TypeError("arguments must be an exact tuple")
    if any(
        argument is not None and type(argument) is not LogicalTypeIdentity
        for argument in arguments
    ):
        raise TypeError("arguments require exact LogicalTypeIdentity or None members")

    evaluations = tuple(
        CandidateEvaluation(
            index=index,
            result=bind_signature(signature, arguments),
        )
        for index, signature in enumerate(overloads.signatures)
    )
    match_count = sum(
        type(evaluation.result) is SignatureMatch for evaluation in evaluations
    )
    outcome = (
        OverloadOutcome.UNSUPPORTED
        if match_count == 0
        else OverloadOutcome.MATCH
        if match_count == 1
        else OverloadOutcome.AMBIGUOUS
    )
    return OverloadSelection(outcome=outcome, evaluations=evaluations)
