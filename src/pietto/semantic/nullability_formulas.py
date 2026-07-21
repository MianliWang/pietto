"""Private symbolic result-nullability formula foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto.semantic.generic_compatibility import GenericSignature, ParameterDefault
from pietto.semantic.model import EffectiveNullability

__all__: tuple[str, ...] = ()

_MAX_FORMULA_DEPTH = 2
_MAX_FORMULA_NODES = 3
_MAX_ARGUMENT_REFERENCE_OCCURRENCES = 2


class NullabilityFormulaKind(StrEnum):
    """Exact private symbolic result-nullability formula kinds."""

    NON_NULL = "non_null"
    NULLABLE = "nullable"
    SAME_AS_ARG = "same_as_arg"
    ANY_NULLABLE = "any_nullable"
    ALWAYS_NULLABLE = "always_nullable"
    NULLABLE_IF_DEFAULT_OMITTED = "nullable_if_default_omitted"
    ANY_OF = "any_of"


def _require_nonnegative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field_name} must be an exact int")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _require_effective_nullability(
    value: object,
    field_name: str,
) -> EffectiveNullability:
    if type(value) is not EffectiveNullability:
        raise TypeError(f"{field_name} must be an exact EffectiveNullability")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class NonNullFormula:
    """A constant non-null result formula."""

    kind: NullabilityFormulaKind = field(
        default=NullabilityFormulaKind.NON_NULL,
        init=False,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class NullableFormula:
    """An explicit literal nullable algebra factor."""

    kind: NullabilityFormulaKind = field(
        default=NullabilityFormulaKind.NULLABLE,
        init=False,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class SameAsArgumentFormula:
    """A formula that preserves one supplied argument's nullability."""

    argument_index: int
    kind: NullabilityFormulaKind = field(
        default=NullabilityFormulaKind.SAME_AS_ARG,
        init=False,
    )

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.argument_index, "argument_index")


@dataclass(frozen=True, slots=True, kw_only=True)
class AnyNullableFormula:
    """An ordered one-or-two-argument three-state nullability join."""

    argument_indices: tuple[int, ...]
    kind: NullabilityFormulaKind = field(
        default=NullabilityFormulaKind.ANY_NULLABLE,
        init=False,
    )

    def __post_init__(self) -> None:
        if type(self.argument_indices) is not tuple:
            raise TypeError("argument_indices must be an exact tuple")
        if len(self.argument_indices) not in {1, 2}:
            raise ValueError("argument_indices must contain one or two positions")
        for index in self.argument_indices:
            _require_nonnegative_int(index, "argument index")


@dataclass(frozen=True, slots=True, kw_only=True)
class AlwaysNullableFormula:
    """A context-independent nullable signature-result policy."""

    kind: NullabilityFormulaKind = field(
        default=NullabilityFormulaKind.ALWAYS_NULLABLE,
        init=False,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class NullableIfDefaultOmittedFormula:
    """A nullable factor controlled by one validated default omission."""

    parameter_index: int
    kind: NullabilityFormulaKind = field(
        default=NullabilityFormulaKind.NULLABLE_IF_DEFAULT_OMITTED,
        init=False,
    )

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.parameter_index, "parameter_index")


@dataclass(frozen=True, slots=True, kw_only=True)
class AnyOfFormula:
    """An ordered binary three-state OR composition."""

    children: tuple[NullabilityFormula, NullabilityFormula]
    kind: NullabilityFormulaKind = field(
        default=NullabilityFormulaKind.ANY_OF,
        init=False,
    )

    def __post_init__(self) -> None:
        if type(self.children) is not tuple:
            raise TypeError("children must be an exact tuple")
        if len(self.children) != 2:
            raise ValueError("children must contain exactly two formulas")
        if any(not _is_formula(child) for child in self.children):
            raise TypeError("children require exact nullability formula variants")


type NullabilityFormula = (
    NonNullFormula
    | NullableFormula
    | SameAsArgumentFormula
    | AnyNullableFormula
    | AlwaysNullableFormula
    | NullableIfDefaultOmittedFormula
    | AnyOfFormula
)


def _is_formula(value: object) -> bool:
    return type(value) in {
        NonNullFormula,
        NullableFormula,
        SameAsArgumentFormula,
        AnyNullableFormula,
        AlwaysNullableFormula,
        NullableIfDefaultOmittedFormula,
        AnyOfFormula,
    }


def _formula_metrics(formula: NullabilityFormula) -> tuple[int, int, int]:
    if type(formula) is AnyOfFormula:
        child_metrics = tuple(_formula_metrics(child) for child in formula.children)
        return (
            1 + max(metrics[0] for metrics in child_metrics),
            1 + sum(metrics[1] for metrics in child_metrics),
            sum(metrics[2] for metrics in child_metrics),
        )
    if type(formula) is SameAsArgumentFormula:
        return (1, 1, 1)
    if type(formula) is AnyNullableFormula:
        return (1, 1, len(formula.argument_indices))
    return (1, 1, 0)


def _walk_formula(formula: NullabilityFormula) -> tuple[NullabilityFormula, ...]:
    if type(formula) is AnyOfFormula:
        return (
            formula,
            *(_walk_formula(formula.children[0])),
            *(_walk_formula(formula.children[1])),
        )
    return (formula,)


@dataclass(frozen=True, slots=True, kw_only=True)
class SignatureResultFormula:
    """An exact generic signature with a private result-nullability formula."""

    signature: GenericSignature
    nullability: NullabilityFormula

    def __post_init__(self) -> None:
        if type(self.signature) is not GenericSignature:
            raise TypeError("signature must be an exact GenericSignature")
        if not _is_formula(self.nullability):
            raise TypeError("nullability must be an exact formula variant")

        depth, nodes, argument_references = _formula_metrics(self.nullability)
        if depth > _MAX_FORMULA_DEPTH:
            raise ValueError("formula depth exceeds the exact maximum")
        if nodes > _MAX_FORMULA_NODES:
            raise ValueError("formula node count exceeds the exact maximum")
        if argument_references > _MAX_ARGUMENT_REFERENCE_OCCURRENCES:
            raise ValueError("formula argument references exceed the exact maximum")

        parameter_count = len(self.signature.parameters)
        formula_nodes = _walk_formula(self.nullability)
        for formula in formula_nodes:
            if type(formula) is SameAsArgumentFormula:
                indices = (formula.argument_index,)
            elif type(formula) is AnyNullableFormula:
                indices = formula.argument_indices
            elif type(formula) is NullableIfDefaultOmittedFormula:
                indices = (formula.parameter_index,)
            else:
                indices = ()
            if any(index >= parameter_count for index in indices):
                raise ValueError("formula parameter index is outside the signature")

        default_formulas = tuple(
            formula
            for formula in formula_nodes
            if type(formula) is NullableIfDefaultOmittedFormula
        )
        for formula in default_formulas:
            parameter = self.signature.parameters[formula.parameter_index]
            if not parameter.optional:
                raise ValueError("default omission reference requires optional=True")
        for formula in default_formulas:
            parameter = self.signature.parameters[formula.parameter_index]
            if parameter.default is not ParameterDefault.OMITTED:
                raise ValueError(
                    "default omission reference requires ParameterDefault.OMITTED"
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class NullabilityEvaluationContext:
    """Ordered supplied facts and exact omitted suffix positions."""

    argument_nullabilities: tuple[EffectiveNullability, ...]
    omitted_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.argument_nullabilities) is not tuple:
            raise TypeError("argument_nullabilities must be an exact tuple")
        for value in self.argument_nullabilities:
            _require_effective_nullability(value, "argument nullability")
        if type(self.omitted_positions) is not tuple:
            raise TypeError("omitted_positions must be an exact tuple")
        for position in self.omitted_positions:
            _require_nonnegative_int(position, "omitted position")
        if self.omitted_positions != tuple(sorted(set(self.omitted_positions))):
            raise ValueError("omitted_positions must be strictly ascending and unique")


class NullabilityEvaluationFailureReason(StrEnum):
    """Exact private structured evaluation failure reasons."""

    CONTEXT_ARITY_MISMATCH = "context_arity_mismatch"
    INVALID_OMISSION_CONTEXT = "invalid_omission_context"
    REQUIRED_PARAMETER_OMITTED = "required_parameter_omitted"
    MISSING_ARGUMENT_NULLABILITY = "missing_argument_nullability"
    OMITTED_ARGUMENT_REFERENCED = "omitted_argument_referenced"


def _join_nullabilities(
    values: tuple[EffectiveNullability, ...],
) -> EffectiveNullability:
    if EffectiveNullability.NULLABLE in values:
        return EffectiveNullability.NULLABLE
    if EffectiveNullability.UNKNOWN in values:
        return EffectiveNullability.UNKNOWN
    return EffectiveNullability.NON_NULL


@dataclass(frozen=True, slots=True, kw_only=True)
class NullabilityArgumentEvidence:
    """One ordered argument occurrence and its concrete join contribution."""

    parameter_position: int
    supplied: bool
    value: EffectiveNullability | None
    contribution: EffectiveNullability

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.parameter_position, "parameter_position")
        if type(self.supplied) is not bool:
            raise TypeError("supplied must be an exact bool")
        _require_effective_nullability(self.contribution, "contribution")
        if self.supplied:
            _require_effective_nullability(self.value, "supplied value")
            if self.contribution is not self.value:
                raise ValueError("supplied contribution must equal the value")
        else:
            if self.value is not None:
                raise ValueError("omitted argument evidence must have value=None")
            if self.contribution is not EffectiveNullability.NON_NULL:
                raise ValueError("omitted argument contribution must be NON_NULL")


@dataclass(frozen=True, slots=True, kw_only=True)
class NullabilityDefaultEvidence:
    """One validated default position and its omission contribution."""

    parameter_position: int
    omitted: bool
    contribution: EffectiveNullability

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.parameter_position, "parameter_position")
        if type(self.omitted) is not bool:
            raise TypeError("omitted must be an exact bool")
        _require_effective_nullability(self.contribution, "contribution")
        expected = (
            EffectiveNullability.NULLABLE
            if self.omitted
            else EffectiveNullability.NON_NULL
        )
        if self.contribution is not expected:
            raise ValueError("default contribution must match omission state")


@dataclass(frozen=True, slots=True, kw_only=True)
class NullabilityEvaluationEvidence:
    """Recursive ordered evidence for one formula result."""

    kind: NullabilityFormulaKind
    value: EffectiveNullability
    arguments: tuple[NullabilityArgumentEvidence, ...] = ()
    default: NullabilityDefaultEvidence | None = None
    children: tuple[NullabilityEvaluationEvidence, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not NullabilityFormulaKind:
            raise TypeError("kind must be an exact NullabilityFormulaKind")
        _require_effective_nullability(self.value, "evidence value")
        if type(self.arguments) is not tuple:
            raise TypeError("arguments must be an exact tuple")
        if any(
            type(item) is not NullabilityArgumentEvidence for item in self.arguments
        ):
            raise TypeError("arguments require exact evidence members")
        if (
            self.default is not None
            and type(self.default) is not NullabilityDefaultEvidence
        ):
            raise TypeError("default must be exact evidence or None")
        if type(self.children) is not tuple:
            raise TypeError("children must be an exact tuple")
        if any(
            type(item) is not NullabilityEvaluationEvidence for item in self.children
        ):
            raise TypeError("children require exact evidence members")

        if self.kind in {
            NullabilityFormulaKind.NON_NULL,
            NullabilityFormulaKind.NULLABLE,
            NullabilityFormulaKind.ALWAYS_NULLABLE,
        }:
            if self.arguments or self.default is not None or self.children:
                raise ValueError("constant evidence cannot have nested payload")
            expected = (
                EffectiveNullability.NON_NULL
                if self.kind is NullabilityFormulaKind.NON_NULL
                else EffectiveNullability.NULLABLE
            )
            if self.value is not expected:
                raise ValueError("constant evidence value must match its kind")
        elif self.kind is NullabilityFormulaKind.SAME_AS_ARG:
            if len(self.arguments) != 1 or self.default is not None or self.children:
                raise ValueError("SAME_AS_ARG evidence requires one argument")
            if self.value is not self.arguments[0].contribution:
                raise ValueError("SAME_AS_ARG evidence value must match its argument")
        elif self.kind is NullabilityFormulaKind.ANY_NULLABLE:
            if (
                len(self.arguments) not in {1, 2}
                or self.default is not None
                or self.children
            ):
                raise ValueError("ANY_NULLABLE evidence requires one or two arguments")
            if self.value is not _join_nullabilities(
                tuple(item.contribution for item in self.arguments)
            ):
                raise ValueError("ANY_NULLABLE evidence value must match its arguments")
        elif self.kind is NullabilityFormulaKind.NULLABLE_IF_DEFAULT_OMITTED:
            if self.arguments or self.default is None or self.children:
                raise ValueError("default formula evidence requires one default row")
            if self.value is not self.default.contribution:
                raise ValueError("default evidence value must match its contribution")
        else:
            if self.arguments or self.default is not None or len(self.children) != 2:
                raise ValueError("ANY_OF evidence requires exactly two children")
            if self.value is not _join_nullabilities(
                tuple(child.value for child in self.children)
            ):
                raise ValueError("ANY_OF evidence value must match its children")


@dataclass(frozen=True, slots=True, kw_only=True)
class NullabilityEvaluationMatch:
    """A successful concrete nullability result with ordered evidence."""

    value: EffectiveNullability
    evidence: NullabilityEvaluationEvidence

    def __post_init__(self) -> None:
        _require_effective_nullability(self.value, "match value")
        if type(self.evidence) is not NullabilityEvaluationEvidence:
            raise TypeError("evidence must be exact NullabilityEvaluationEvidence")
        if self.value is not self.evidence.value:
            raise ValueError("match value must equal evidence value")


@dataclass(frozen=True, slots=True, kw_only=True)
class NullabilityEvaluationUnsupported:
    """A structured private failure for an incompatible evaluation context."""

    reason: NullabilityEvaluationFailureReason
    parameter_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.reason) is not NullabilityEvaluationFailureReason:
            raise TypeError("reason must be an exact evaluation failure reason")
        if self.parameter_position is not None:
            _require_nonnegative_int(self.parameter_position, "parameter_position")
        position_required = self.reason in {
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            NullabilityEvaluationFailureReason.REQUIRED_PARAMETER_OMITTED,
            NullabilityEvaluationFailureReason.MISSING_ARGUMENT_NULLABILITY,
            NullabilityEvaluationFailureReason.OMITTED_ARGUMENT_REFERENCED,
        }
        if position_required and self.parameter_position is None:
            raise ValueError("failure reason requires a parameter position")
        if (
            self.reason is NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH
            and self.parameter_position is not None
        ):
            raise ValueError("context arity mismatch cannot have a position")


type NullabilityEvaluationResult = (
    NullabilityEvaluationMatch | NullabilityEvaluationUnsupported
)


def _argument_evidence(
    position: int,
    context: NullabilityEvaluationContext,
) -> NullabilityArgumentEvidence:
    if position < len(context.argument_nullabilities):
        value = context.argument_nullabilities[position]
        return NullabilityArgumentEvidence(
            parameter_position=position,
            supplied=True,
            value=value,
            contribution=value,
        )
    return NullabilityArgumentEvidence(
        parameter_position=position,
        supplied=False,
        value=None,
        contribution=EffectiveNullability.NON_NULL,
    )


def _evaluate_formula(
    formula: NullabilityFormula,
    context: NullabilityEvaluationContext,
) -> NullabilityEvaluationResult:
    if type(formula) is NonNullFormula:
        evidence = NullabilityEvaluationEvidence(
            kind=formula.kind,
            value=EffectiveNullability.NON_NULL,
        )
        return NullabilityEvaluationMatch(value=evidence.value, evidence=evidence)
    if type(formula) is NullableFormula:
        evidence = NullabilityEvaluationEvidence(
            kind=formula.kind,
            value=EffectiveNullability.NULLABLE,
        )
        return NullabilityEvaluationMatch(value=evidence.value, evidence=evidence)
    if type(formula) is AlwaysNullableFormula:
        evidence = NullabilityEvaluationEvidence(
            kind=formula.kind,
            value=EffectiveNullability.NULLABLE,
        )
        return NullabilityEvaluationMatch(value=evidence.value, evidence=evidence)
    if type(formula) is SameAsArgumentFormula:
        if formula.argument_index in context.omitted_positions:
            return NullabilityEvaluationUnsupported(
                reason=(NullabilityEvaluationFailureReason.OMITTED_ARGUMENT_REFERENCED),
                parameter_position=formula.argument_index,
            )
        argument = _argument_evidence(formula.argument_index, context)
        evidence = NullabilityEvaluationEvidence(
            kind=formula.kind,
            value=argument.contribution,
            arguments=(argument,),
        )
        return NullabilityEvaluationMatch(value=evidence.value, evidence=evidence)
    if type(formula) is AnyNullableFormula:
        arguments = tuple(
            _argument_evidence(position, context)
            for position in formula.argument_indices
        )
        evidence = NullabilityEvaluationEvidence(
            kind=formula.kind,
            value=_join_nullabilities(
                tuple(argument.contribution for argument in arguments)
            ),
            arguments=arguments,
        )
        return NullabilityEvaluationMatch(value=evidence.value, evidence=evidence)
    if type(formula) is NullableIfDefaultOmittedFormula:
        omitted = formula.parameter_index in context.omitted_positions
        default = NullabilityDefaultEvidence(
            parameter_position=formula.parameter_index,
            omitted=omitted,
            contribution=(
                EffectiveNullability.NULLABLE
                if omitted
                else EffectiveNullability.NON_NULL
            ),
        )
        evidence = NullabilityEvaluationEvidence(
            kind=formula.kind,
            value=default.contribution,
            default=default,
        )
        return NullabilityEvaluationMatch(value=evidence.value, evidence=evidence)

    assert isinstance(formula, AnyOfFormula)
    child_results = tuple(
        _evaluate_formula(child, context) for child in formula.children
    )
    for result in child_results:
        if type(result) is NullabilityEvaluationUnsupported:
            return result
    child_matches = tuple(
        result for result in child_results if type(result) is NullabilityEvaluationMatch
    )
    assert len(child_matches) == 2
    evidence = NullabilityEvaluationEvidence(
        kind=formula.kind,
        value=_join_nullabilities(tuple(child.value for child in child_matches)),
        children=tuple(child.evidence for child in child_matches),
    )
    return NullabilityEvaluationMatch(value=evidence.value, evidence=evidence)


def evaluate_signature_result_nullability(
    association: SignatureResultFormula,
    context: NullabilityEvaluationContext,
) -> NullabilityEvaluationResult:
    """Evaluate one validated signature-result formula over concrete facts."""

    if type(association) is not SignatureResultFormula:
        raise TypeError("association must be an exact SignatureResultFormula")
    if type(context) is not NullabilityEvaluationContext:
        raise TypeError("context must be an exact NullabilityEvaluationContext")

    parameters = association.signature.parameters
    minimum_required = sum(not parameter.optional for parameter in parameters)
    maximum = len(parameters)
    actual = len(context.argument_nullabilities)
    if actual > maximum:
        return NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH
        )
    if actual < minimum_required:
        return NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.REQUIRED_PARAMETER_OMITTED,
            parameter_position=actual,
        )

    expected_omitted = tuple(range(actual, maximum))
    omitted_set = set(context.omitted_positions)
    for position in expected_omitted:
        if position not in omitted_set:
            return NullabilityEvaluationUnsupported(
                reason=(
                    NullabilityEvaluationFailureReason.MISSING_ARGUMENT_NULLABILITY
                ),
                parameter_position=position,
            )
    if context.omitted_positions != expected_omitted:
        offending = next(
            (
                position
                for position in context.omitted_positions
                if position not in expected_omitted
            ),
            None,
        )
        return NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            parameter_position=offending,
        )
    return _evaluate_formula(association.nullability, context)
