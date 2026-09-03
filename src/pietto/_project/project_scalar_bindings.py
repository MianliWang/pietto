"""Private Phase-63 authored JOIN binding and visible-field lookup authority."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.project_ir import ProjectIRJoinInputUseOccurrence
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinOccurrence,
    ProjectIRConcreteJoinRegion,
)
from pietto._project.project_ir_properties import ProjectIRJoinedRowField
from pietto._project.project_query_block import ProjectVerifiedJoinedRowSource
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectJoinUseState,
    ProjectRelationBindingOccurrence,
    ProjectRelationJoinUseLedger,
)
from pietto._project.project_scalar_references import (
    ProjectConcreteScalarEnvironment,
    ProjectScalarEnvironmentField,
    ProjectScalarReferenceOccurrence,
    ProjectScalarReferenceResolution,
)
from pietto.ast_nodes import DottedNameExpr, NameExpr

__all__: tuple[str, ...] = ()


def _binding_introduction_use(
    region: ProjectIRConcreteJoinRegion,
    binding: ProjectRelationBindingOccurrence,
) -> ProjectIRJoinInputUseOccurrence:
    position = binding.identity.binding_position
    if position == 0:
        return region.joins[0].input_uses[0]
    use = region.ledger.uses[position - 1]
    if type(use) is not ProjectConcreteJoinUse:
        raise ValueError("Visible binding requires an exact concrete JOIN use.")
    terminal_position = len(use.path.steps) - 1
    matches = tuple(
        join
        for join in region.joins
        if join.use is use and join.identity.path_step_position == terminal_position
    )
    if len(matches) != 1:
        raise ValueError("JOIN target binding requires one exact terminal path step.")
    terminal = matches[0]
    if terminal.use is not use or (
        terminal.identity.path_step_position != len(terminal.use.path.steps) - 1
    ):
        raise ValueError("JOIN target binding lost its terminal provenance.")
    return terminal.input_uses[1]


def _joined_environment_field(
    environment: ProjectConcreteScalarEnvironment,
    candidate: ProjectScalarEnvironmentField,
) -> ProjectIRJoinedRowField:
    if not any(candidate is retained for retained in environment.fields):
        raise ValueError("Visible field must belong to its exact scalar environment.")
    source_field = candidate.source_field
    if type(source_field) is not ProjectIRJoinedRowField:
        raise TypeError("Joined visibility requires exact joined field occurrences.")
    return source_field


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectVisibleJoinedBinding:
    """One exact authored Phase-62 binding and its final visible occurrences."""

    scalar_environment: ProjectConcreteScalarEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    binding: ProjectRelationBindingOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    introduction_use: ProjectIRJoinInputUseOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    fields: tuple[ProjectScalarEnvironmentField, ...]

    def __post_init__(self) -> None:
        if type(self.scalar_environment) is not ProjectConcreteScalarEnvironment:
            raise TypeError("Visible binding requires a concrete scalar environment.")
        if type(self.binding) is not ProjectRelationBindingOccurrence or (
            self.binding.state is not ProjectJoinUseState.CONCRETE
        ):
            raise ValueError("Visible binding requires exact concrete authority.")
        if type(self.introduction_use) is not ProjectIRJoinInputUseOccurrence:
            raise TypeError("Visible binding requires an exact introduction use.")
        if type(self.fields) is not tuple or any(
            type(item) is not ProjectScalarEnvironmentField for item in self.fields
        ):
            raise TypeError("Visible binding fields must be an exact tuple.")
        if len({id(item) for item in self.fields}) != len(self.fields):
            raise ValueError("Visible binding fields cannot repeat an occurrence.")
        for item in self.fields:
            source = _joined_environment_field(self.scalar_environment, item)
            if source.introduction_use is not self.introduction_use:
                raise ValueError("Visible fields require exact JOIN provenance.")
        if tuple(item.position for item in self.fields) != tuple(
            sorted(item.position for item in self.fields)
        ):
            raise ValueError("Visible binding fields must retain final row order.")


def _nonterminal_right_introductions(
    joins: tuple[ProjectIRBinaryJoinOccurrence, ...],
) -> tuple[ProjectIRJoinInputUseOccurrence, ...]:
    return tuple(
        join.input_uses[1]
        for join in joins
        if join.identity.path_step_position < len(join.use.path.steps) - 1
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedScalarBindingEnvironment:
    """Exact authored bindings plus visible/hidden final joined occurrences."""

    scalar_environment: ProjectConcreteScalarEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    row_source: ProjectVerifiedJoinedRowSource = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    region: ProjectIRConcreteJoinRegion = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    ledger: ProjectRelationJoinUseLedger = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    bindings: tuple[ProjectVisibleJoinedBinding, ...] = field(init=False)
    visible_fields: tuple[ProjectScalarEnvironmentField, ...] = field(init=False)
    hidden_fields: tuple[ProjectScalarEnvironmentField, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.scalar_environment) is not ProjectConcreteScalarEnvironment:
            raise TypeError("Joined bindings require a concrete scalar environment.")
        row_source = self.scalar_environment.row_source
        if type(row_source) is not ProjectVerifiedJoinedRowSource:
            raise TypeError("Joined bindings require a verified joined row source.")
        region = row_source.region
        ledger = region.ledger
        if type(region) is not ProjectIRConcreteJoinRegion or (
            type(ledger) is not ProjectRelationJoinUseLedger
        ):
            raise TypeError("Joined bindings require exact Phase-62 roots.")
        if any(
            type(binding) is not ProjectRelationBindingOccurrence
            or binding.state is not ProjectJoinUseState.CONCRETE
            for binding in ledger.bindings
        ):
            raise ValueError(
                "Concrete joined bindings require concrete ledger entries."
            )
        names = tuple(binding.name for binding in ledger.bindings)
        if len(set(names)) != len(names):
            raise ValueError("Concrete joined binding names must be unique.")
        scalar_fields = self.scalar_environment.fields
        for item in scalar_fields:
            _joined_environment_field(self.scalar_environment, item)

        introductions = tuple(
            _binding_introduction_use(region, binding) for binding in ledger.bindings
        )
        if len({id(item) for item in introductions}) != len(introductions):
            raise ValueError("Authored bindings require distinct introduction uses.")
        visible_bindings = tuple(
            ProjectVisibleJoinedBinding(
                scalar_environment=self.scalar_environment,
                binding=binding,
                introduction_use=introduction,
                fields=tuple(
                    item
                    for item in scalar_fields
                    if _joined_environment_field(
                        self.scalar_environment,
                        item,
                    ).introduction_use
                    is introduction
                ),
            )
            for binding, introduction in zip(
                ledger.bindings,
                introductions,
                strict=True,
            )
        )
        visible_ids = {
            id(item) for binding in visible_bindings for item in binding.fields
        }
        visible_fields = tuple(
            item for item in scalar_fields if id(item) in visible_ids
        )
        hidden_fields = tuple(
            item for item in scalar_fields if id(item) not in visible_ids
        )
        if len(visible_fields) + len(hidden_fields) != len(scalar_fields) or len(
            visible_ids
        ) != len(visible_fields):
            raise ValueError(
                "Visible and hidden fields must exactly partition the row."
            )
        nonterminal_introductions = _nonterminal_right_introductions(region.joins)
        if any(
            not any(
                _joined_environment_field(
                    self.scalar_environment,
                    item,
                ).introduction_use
                is introduction
                for introduction in nonterminal_introductions
            )
            for item in hidden_fields
        ):
            raise ValueError("Hidden fields require non-terminal path provenance.")
        object.__setattr__(self, "row_source", row_source)
        object.__setattr__(self, "region", region)
        object.__setattr__(self, "ledger", ledger)
        object.__setattr__(self, "bindings", visible_bindings)
        object.__setattr__(self, "visible_fields", visible_fields)
        object.__setattr__(self, "hidden_fields", hidden_fields)


def build_project_joined_scalar_binding_environment(
    scalar_environment: ProjectConcreteScalarEnvironment,
) -> ProjectJoinedScalarBindingEnvironment:
    """Build joined visibility only from one exact Slice-3 concrete environment."""

    return ProjectJoinedScalarBindingEnvironment(
        scalar_environment=scalar_environment,
    )


def resolve_project_joined_scalar_reference(
    binding_environment: ProjectJoinedScalarBindingEnvironment,
    reference: ProjectScalarReferenceOccurrence,
) -> ProjectScalarReferenceResolution:
    """Discover exact visible candidates without changing Slice-3 classification."""

    if type(binding_environment) is not ProjectJoinedScalarBindingEnvironment:
        raise TypeError("Joined lookup requires an exact binding environment.")
    if type(reference) is not ProjectScalarReferenceOccurrence or (
        reference.environment is not binding_environment.scalar_environment
    ):
        raise ValueError("Joined lookup requires an exact same-root reference.")
    expression = reference.expression
    if type(expression) is NameExpr:
        candidates = tuple(
            item
            for item in binding_environment.visible_fields
            if item.evidence.name == expression.name
        )
    elif type(expression) is DottedNameExpr:
        if len(expression.parts) != 2:
            candidates = ()
        else:
            qualifier, field_name = expression.parts
            bindings = tuple(
                binding
                for binding in binding_environment.bindings
                if binding.binding.name == qualifier
            )
            if len(bindings) > 1:
                raise ValueError("Concrete binding qualifier must be unique.")
            candidates = (
                ()
                if not bindings
                else tuple(
                    item
                    for item in bindings[0].fields
                    if item.evidence.name == field_name
                )
            )
    else:
        raise AssertionError("scalar reference lost its exact expression variant")
    return ProjectScalarReferenceResolution(
        reference=reference,
        candidates=candidates,
    )
