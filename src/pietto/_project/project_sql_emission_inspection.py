"""Immutable artifact-bound inspection: denominators, result chains and SQL ranges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from pietto._project.project_sql_plan import ProjectSQLPlanRef, ProjectSQLPlanRefKind
from pietto._project.project_sql_plan_source_maps import ProjectSQLSourceMapEntry
from pietto._project.project_sql_emission_contract import PreparedEmission
from pietto._project.project_sql_emission_rendering import RenderingEvent
from pietto._project.project_sql_emission_verification import (
    EmissionVerification,
    verify_project_sql_emission,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class SQLRange:
    """One retained token event or expression overlay over the exact SQL bytes.

    `position` is the range's index in the retained sequence: every token event
    in byte order, then every expression overlay in its retained order. `origins`
    pairs each retained source-map entry of the subject with that entry's
    retained source associations; scaffolding with no authored span keeps an
    empty tuple rather than an invented location.
    """

    position: int
    kind: str
    role: str
    subject: object
    start: int
    end: int
    event: RenderingEvent
    origins: tuple[tuple[Any, tuple[Any, ...]], ...]

    def __repr__(self) -> str:
        return (
            f"SQLRange(position={self.position}, kind={self.kind!r}, "
            f"role={self.role!r}, start={self.start}, end={self.end}, "
            f"origins=<{len(self.origins)}>)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class EmissionInspection:
    """A read-only view over one verified artifact and its exact prepared request.

    Every field is a retained runtime object or a bounded tuple over retained
    objects; nothing here is rebuilt, rendered or reopened. Queries are bounded
    linear scans of `ranges`.
    """

    artifact: Any
    request: PreparedEmission
    verification: EmissionVerification
    sql: bytes
    ranges: tuple[SQLRange, ...]
    original_requirements: tuple[Any, ...]
    generated_requirements: tuple[Any, ...]
    columns: tuple[Any, ...]
    parameter_uses: tuple[tuple[Any, SQLRange], ...]

    def __repr__(self) -> str:
        return (
            "EmissionInspection(artifact=..., request=..., "
            f"sql=<{len(self.sql)} bytes>, ranges=<{len(self.ranges)}>, "
            f"original_requirements=<{len(self.original_requirements)}>, "
            f"generated_requirements=<{len(self.generated_requirements)}>, "
            f"columns=<{len(self.columns)}>, "
            f"parameter_uses=<{len(self.parameter_uses)}>)"
        )

    def _offset(self, value, *, name):
        if type(value) is not int or value < 0 or value > len(self.sql):
            raise ValueError(f"{name} must be an int within [0, len(sql)].")
        return value

    def at(self, offset: int) -> tuple[SQLRange, ...]:
        """Every range with `start <= offset < end`; `len(sql)` has no hit."""
        point = self._offset(offset, name="offset")
        return tuple(r for r in self.ranges if r.start <= point < r.end)

    def overlapping(self, start: int, end: int) -> tuple[SQLRange, ...]:
        """Every range overlapping the nonempty half-open byte interval."""
        low = self._offset(start, name="start")
        high = self._offset(end, name="end")
        if high < low:
            raise ValueError("Interval ends before its start.")
        if high == low:
            return ()
        return tuple(r for r in self.ranges if r.start < high and low < r.end)

    def ranges_of(self, reference) -> tuple[SQLRange, ...]:
        """All ranges of one exact retained subject, or of one retained origin.

        A subject that emitted nothing yields an empty tuple; a reference that
        is not the retained object itself is foreign and is rejected.
        """
        indexes = self.request.source_map.source_map.indexes
        if type(reference) is ProjectSQLSourceMapEntry:
            if indexes.origins.get(reference.ref) is not reference:
                raise ValueError("Origin is not a retained source-map entry.")
            entry = reference
        elif (
            type(reference) is ProjectSQLPlanRef
            and reference.kind is ProjectSQLPlanRefKind.ORIGIN
        ):
            entry = indexes.origins.get(reference)
            if entry is None:
                raise ValueError("Reference is not a retained origin.")
        else:
            try:
                known = reference in indexes.subjects
            except TypeError:
                known = False
            if not known and not any(r.subject is reference for r in self.ranges):
                raise ValueError("Reference is not a retained emission subject.")
            return tuple(r for r in self.ranges if r.subject is reference)
        return tuple(r for r in self.ranges if any(e is entry for e in r.event.origins))


def inspect_project_sql_emission(artifact, request) -> EmissionInspection:
    """Bind one runtime artifact to its prepared request after complete verification."""
    from pietto._project.project_sql_emission import EmissionArtifact

    if (
        type(artifact) is not EmissionArtifact
        or type(request) is not PreparedEmission
        or artifact.request is not request
    ):
        raise ValueError(
            "Emission inspection requires the exact runtime artifact and its request."
        )
    checked = verify_project_sql_emission(artifact, request)
    if not checked.verified:
        raise ValueError(
            "Emission inspection requires a verified artifact: "
            + ", ".join(checked.issues)
        )
    associations = request.source_map.source_map.indexes.associations
    rendered = artifact.rendered
    ranges = tuple(
        SQLRange(
            position,
            event.kind,
            event.role,
            event.subject,
            event.start,
            event.end,
            event,
            tuple(
                (entry, associations[entry.ref])
                for entry in cast(tuple[Any, ...], event.origins)
            ),
        )
        for position, event in enumerate(
            (*rendered.events, *rendered.expression_ranges)
        )
    )
    tokens = tuple(r for r in ranges if r.kind == "parameter")
    ast: Any = artifact.ast
    units = getattr(ast, "units", None) or getattr(ast, "bodies", None) or (ast,)
    return EmissionInspection(
        artifact,
        request,
        checked,
        rendered.sql,
        ranges,
        artifact.original_requirements,
        artifact.generated_requirements,
        tuple(units[-1].columns),
        tuple(zip(artifact.parameter_uses, tokens, strict=True)),
    )
