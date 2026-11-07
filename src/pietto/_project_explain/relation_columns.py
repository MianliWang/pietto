"""Private relation column view of a schema version 2 project.

``explain --project`` routes a schema version 2 (explicit-module)
configuration here, as the runtime builder's ``_lists_relation_columns``
decides, and writes ``pietto.project-relation-columns.v1``. The view only
inspects: it maps the row field facts that the completed project semantics
hold for each table and query, infers and repairs nothing, builds no IR, and
fails closed when a fact is absent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from pietto._project.check import (
    check_project_parse_only,
    project_recursion_limit_diagnostic,
)
from pietto._project.json_v2 import (
    _cli_error_to_json_dict,
    _diagnostic_to_json_dict,
    module_related_locations,
)
from pietto._project.model import (
    NESTED_RELATION_TYPE_NAME,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_completion import ProjectExistingEffectiveOutput
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectCompletedSetOutput,
    ProjectCompletedValuesOutput,
)
from pietto._project.project_sql_emission_contract import canonical
from pietto.errors import Diagnostic, SourceLocation

__all__: tuple[str, ...] = ()

FORMAT = "pietto.project-relation-columns.v1"
_KINDS = ("table", "query")
_TYPE_KINDS = {
    ProjectResolvedTypeKind.BUILTIN: "builtin",
    ProjectResolvedTypeKind.TYPE_ALIAS: "type_alias",
    ProjectResolvedTypeKind.ENUM: "enum",
    ProjectResolvedTypeKind.SHAPE: "shape",
    ProjectResolvedTypeKind.UNKNOWN: "unknown",
}
# The kinds whose type object names the module that declares the type.
_DECLARED = {
    ProjectResolvedTypeKind.ENUM: ProjectSymbolKind.ENUM,
    ProjectResolvedTypeKind.SHAPE: ProjectSymbolKind.SHAPE,
}
# Internal type names that no public output shows.
_SENTINELS = frozenset({NESTED_RELATION_TYPE_NAME, "<unknown>"})
_UNAVAILABLE = ProjectDiscoveryError(
    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
    "Project relation columns are unavailable.",
)


class _Unavailable(Exception):
    """A fact the view needs is absent, so it publishes no columns."""


@dataclass(frozen=True, slots=True)
class RelationColumn:
    """One output column; ``element`` holds a collection's columns and
    ``type_module`` the module that declares an enum or shape type."""

    name: str
    kind: str
    type_name: str | None
    nullability: str
    element: tuple[RelationColumn, ...] | None = None
    type_module: str | None = None


@dataclass(frozen=True, slots=True)
class RelationColumns:
    """The columns of one table or query, in output order."""

    module: str
    kind: str
    name: str
    columns: tuple[RelationColumn, ...]


@dataclass(frozen=True, slots=True)
class ProjectRelationColumnsResult:
    """One complete outcome: the document parts and the exit code.

    ``related`` holds the related locations of each diagnostic, in order;
    ``relations`` is None exactly when the outcome is a failure.
    """

    exit_code: int
    diagnostics: tuple[Diagnostic, ...]
    related: tuple[tuple[SourceLocation, ...], ...]
    cli_errors: tuple[ProjectDiscoveryError, ...]
    relations: tuple[RelationColumns, ...] | None


def build_project_relation_columns(root: Path) -> ProjectRelationColumnsResult:
    """List the columns of every table and query of one schema 2 project."""

    try:
        parsed = check_project_parse_only(root)
    except (OSError, ValueError):
        return _result(
            2,
            (),
            {},
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_ROOT,
                    "Project root could not be pinned.",
                ),
            ),
        )
    related = dict(module_related_locations(parsed))
    if parsed.errors:
        return _result(2, parsed.diagnostics, related, parsed.errors)
    if parsed.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
        # The routing read found schema version 2; the parse read another.
        return _result(
            2,
            parsed.diagnostics,
            related,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                    "Project configuration changed while explain --project read it.",
                    "pietto.toml",
                ),
            ),
        )
    if not parsed.ok:
        return _result(1, parsed.diagnostics, related)
    diagnostics = parsed.diagnostics
    try:
        semantic = build_empty_project_semantic_result(parsed)
        related.update(module_related_locations(semantic))
        completed = build_project_completed_semantic_result(semantic)
        # As check --project reports them: a diagnostic equal to an earlier
        # one once, at its first position.
        diagnostics = tuple(dict.fromkeys((*diagnostics, *completed.diagnostics)))
        if (
            type(completed) is not ProjectConcreteCompletedSemanticResult
            or not completed.ok
        ):
            return _result(1, diagnostics, related)
        relations = _relations(completed)
    except RecursionError:
        return _result(
            1,
            tuple(
                dict.fromkeys(
                    (*parsed.diagnostics, project_recursion_limit_diagnostic(parsed))
                )
            ),
            related,
        )
    except (TypeError, ValueError, _Unavailable):
        return _result(2, diagnostics, related, (_UNAVAILABLE,))
    return _result(0, diagnostics, related, (), relations)


def _relations(
    completed: ProjectConcreteCompletedSemanticResult,
) -> tuple[RelationColumns, ...]:
    """The tables and queries that emit-sql --project selects, in its order."""

    overlay = completed.effective_outputs
    modules = completed.semantic_result.modules
    paths = frozenset(module.path for module in modules)
    relations: list[RelationColumns] = []
    for owner, entry in zip(overlay.owners, overlay.entries, strict=True):
        kind = owner.identity.declaration_kind.value
        if owner.block_local or kind not in _KINDS:
            continue
        if type(entry) is ProjectExistingEffectiveOutput:
            fields = tuple(item.evidence for item in entry.output.row_shape.fields)
        elif isinstance(
            entry,
            (
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
                ProjectCompletedValuesOutput,
            ),
        ):
            if entry.schema.is_unknown:
                raise _Unavailable
            fields = tuple(entry.schema.fields.values())
        else:
            # A terminal entry under an ok completion.
            raise _Unavailable
        relations.append(
            RelationColumns(
                module=modules[owner.module_position].path,
                kind=kind,
                name=owner.definition.name,
                columns=tuple(_column(item, paths, nested=True) for item in fields),
            )
        )
    return tuple(relations)


def _column(
    field: ProjectRowField, paths: frozenset[str], *, nested: bool
) -> RelationColumn:
    resolved = field.resolved_type
    if resolved.kind is ProjectResolvedTypeKind.NESTED_RELATION:
        descriptor = resolved.nested
        if not nested or descriptor is None:
            raise _Unavailable
        return RelationColumn(
            name=field.name,
            kind="collection",
            type_name=None,
            nullability=field.nullability.value,
            element=tuple(
                _column(item.field, paths, nested=False)
                for item in descriptor.element_fields
            ),
        )
    if resolved.kind not in _TYPE_KINDS or resolved.name in _SENTINELS:
        raise _Unavailable
    module = None
    if resolved.kind in _DECLARED:
        # The declaration the check resolved the type to, past imports and
        # alias chains, which is also its identity in a set operation.
        symbol = resolved.symbol
        if (
            symbol is None
            or symbol.kind is not _DECLARED[resolved.kind]
            or symbol.name != resolved.name
            or symbol.path not in paths
        ):
            raise _Unavailable
        module = symbol.path
    return RelationColumn(
        name=field.name,
        kind=_TYPE_KINDS[resolved.kind],
        type_name=resolved.name,
        nullability=field.nullability.value,
        type_module=module,
    )


def _result(
    exit_code: int,
    diagnostics: tuple[Diagnostic, ...],
    related: dict[Diagnostic, tuple[SourceLocation, ...]],
    cli_errors: tuple[ProjectDiscoveryError, ...] = (),
    relations: tuple[RelationColumns, ...] | None = None,
) -> ProjectRelationColumnsResult:
    """Keep every document UTF-8: a source path that is not valid UTF-8 and
    that the document would name fails it with project_path, as project
    emission does."""

    pairs = tuple((item, related.get(item, ())) for item in diagnostics)
    places = (
        *(relation.module for relation in relations or ()),
        *(
            location.path
            for item, locations in pairs
            for location in (item.location, *locations)
        ),
        *(error.path for error in cli_errors),
    )
    unnamed = next(
        (path for path in places if path is not None and not _utf8(path)), None
    )
    if unnamed is not None:
        exit_code, relations = 2, None
        pairs = tuple(
            (item, locations)
            for item, locations in pairs
            if all(
                location.path is None or _utf8(location.path)
                for location in (item.location, *locations)
            )
        )
        cli_errors = tuple(
            dict.fromkeys(
                (
                    *(
                        error
                        if error.path is None or _utf8(error.path)
                        else replace(error, path=None)
                        for error in cli_errors
                    ),
                    ProjectDiscoveryError(
                        ProjectDiscoveryErrorKind.PROJECT_PATH,
                        "Project source path must be valid UTF-8 to list relation"
                        f" columns: {json.dumps(unnamed)}; rename it.",
                    ),
                )
            )
        )
    return ProjectRelationColumnsResult(
        exit_code=exit_code,
        diagnostics=tuple(
            replace(
                item,
                message=_escaped(item.message),
                suggestion=None
                if item.suggestion is None
                else _escaped(item.suggestion),
            )
            for item, _locations in pairs
        ),
        related=tuple(locations for _item, locations in pairs),
        cli_errors=tuple(
            replace(error, message=_escaped(error.message)) for error in cli_errors
        ),
        relations=relations,
    )


def serialize_project_relation_columns(result: ProjectRelationColumnsResult) -> bytes:
    """The canonical JSON document: sorted keys, no spaces, one final newline."""

    return (
        canonical(
            {
                "cli_errors": [
                    _cli_error_to_json_dict(item) for item in result.cli_errors
                ],
                "diagnostics": [
                    _diagnostic_to_json_dict(item, locations)
                    for item, locations in zip(
                        result.diagnostics, result.related, strict=True
                    )
                ],
                "format": FORMAT,
                "ok": result.relations is not None,
                "relations": None
                if result.relations is None
                else [
                    {
                        "columns": [_column_json(item) for item in relation.columns],
                        "kind": relation.kind,
                        "module": relation.module,
                        "name": relation.name,
                    }
                    for relation in result.relations
                ],
            }
        )
        + b"\n"
    )


def _column_json(column: RelationColumn) -> dict[str, object]:
    column_type: dict[str, object] = {"kind": column.kind, "name": column.type_name}
    if column.type_module is not None:
        column_type["module"] = column.type_module
    if column.element is not None:
        column_type["element"] = [_column_json(item) for item in column.element]
    return {"name": column.name, "nullability": column.nullability, "type": column_type}


def _utf8(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _escaped(text: str) -> str:
    """Text whose characters UTF-8 cannot hold, such as the \\udcff of a file
    name byte, shown as escapes."""

    return text.encode("utf-8", "backslashreplace").decode("utf-8")
