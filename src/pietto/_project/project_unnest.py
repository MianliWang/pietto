"""The element rows of one Unnest occurrence as a zero-input relation (S05)."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.model import (
    ProjectNestedRelationElementField,
    ProjectRowField,
    ProjectRowSchema,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleUnnestOccurrenceFact,
)
from pietto.ast_nodes import UnnestRelationDef
from pietto.errors import Diagnostic

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectUnnestColumn:
    """One element field of an Unnest occurrence: its collected let's output
    field at ``position``, with that child's name, type and nullability; the
    child's identity is its provenance (D-S05-3)."""

    position: int
    child: ProjectNestedRelationElementField = field(repr=False)
    name: str = field(init=False)
    field: ProjectRowField = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.child) is not ProjectNestedRelationElementField
            or self.child.position != self.position
        ):
            raise ValueError("Unnest column requires its exact child field.")
        object.__setattr__(self, "name", self.child.field.name)
        object.__setattr__(self, "field", self.child.field)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectUnnestRelation:
    """The independent facts of one Unnest occurrence's element rows.

    Its rows are those of its argument's nested field in each row of its
    declaration's input that reaches its JOIN: a bag of the collected let's
    rows, without order, keys, functional dependencies or a row bound, even
    when the collected let has them (D-S05-3 N7). It is complete only when
    its input fact types that field; ``diagnostics`` are that fact's own.
    """

    definition: UnnestRelationDef = field(repr=False)
    fact: ProjectModuleUnnestOccurrenceFact = field(repr=False)
    columns: tuple[ProjectUnnestColumn, ...] = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    schema: ProjectRowSchema | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.definition) is not UnnestRelationDef
            or type(self.fact) is not ProjectModuleUnnestOccurrenceFact
            or self.fact.query_let is not self.definition.source
        ):
            raise TypeError("Unnest rows require their exact let and input fact.")
        nested = self.fact.nested_type
        columns = (
            ()
            if nested is None
            else tuple(
                ProjectUnnestColumn(position=item.position, child=item)
                for item in nested.element_fields
            )
        )
        object.__setattr__(self, "columns", columns)
        object.__setattr__(
            self,
            "diagnostics",
            () if self.fact.diagnostic is None else (self.fact.diagnostic,),
        )
        object.__setattr__(
            self,
            "schema",
            None
            if nested is None
            else ProjectRowSchema(fields={c.name: c.field for c in columns}),
        )
