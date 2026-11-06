"""Builtin call names that a source file's own callable declarations shadow.

Kept outside ``pietto.semantic`` so the project model can open the shadowing
scope without importing semantic behaviour.
"""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Iterable, Iterator

from pietto import ast_nodes as ast

__all__: tuple[str, ...] = ()

# A callable a source file declares itself, a `def`, `constraint`, `derive` or
# relationship template, keeps its meaning there over these builtin call
# names, in any declaration order: the `Float` and `Text` constructors, the
# `concat` function and the two-argument `max` and `min` (a `def` of these two
# is refused, PIE-S2398).
_SHADOWABLE = frozenset({"Float", "Text", "concat", "max", "min"})
# The files of the scripts `builtin_shadows` analyzes that declare a callable
# `concat`.
_CONCAT_FILES: contextvars.ContextVar[frozenset[str | None]] = contextvars.ContextVar(
    "_CONCAT_FILES", default=frozenset()
)
# The spans of the nodes that the body of a def or relationship another module
# declares brought into the scripts `builtin_shadows` analyzes. That body is
# bound once, in its module, so a `concat` call in it names the builtin there
# and is no call of the importer's relationship (an import adds no shadow
# scope).
_IMPORTED: contextvars.ContextVar[set[ast.Span] | frozenset[ast.Span]] = (
    contextvars.ContextVar("_IMPORTED", default=frozenset())
)


def shadowed_builtin_names(script: ast.Script) -> frozenset[str]:
    """The builtin call names that a callable ``script`` declares keeps."""

    return frozenset(
        item.name
        for item in script.definitions
        if type(item) in (ast.FunctionDef, ast.ConstraintDef, ast.DeriveDef)
        and item.name in _SHADOWABLE
    ) | frozenset(
        item.name for item in script.relationship_templates if item.name in _SHADOWABLE
    )


@contextlib.contextmanager
def builtin_shadows(
    *scripts: ast.Script,
    defs: Iterable[ast.FunctionDef] = (),
    imported: Iterable[ast.Span] = (),
) -> Iterator[None]:
    """Analyze ``scripts`` inside the block: a `concat` call written in a file
    of one that declares a callable `concat` names that callable, not the
    builtin (`in_concat_file`), as `Float` does (`normalize_float_calls`).
    ``defs`` are a project module's own `def`s, which inlining took out of its
    script; ``imported`` are the nodes of imported def bodies inlining put
    in them (`imported_node`)."""

    imported_token = _IMPORTED.set(set(imported))
    token = _CONCAT_FILES.set(
        frozenset(
            item.span.path
            for script in scripts
            if "concat" in shadowed_builtin_names(script)
            for item in (*script.definitions, *script.relationship_templates)
        )
        | frozenset(item.span.path for item in defs if item.name == "concat")
    )
    try:
        yield
    finally:
        _CONCAT_FILES.reset(token)
        _IMPORTED.reset(imported_token)


def in_concat_file(node: ast.Node) -> bool:
    """Whether ``node`` is written, inside `builtin_shadows`, in a file that
    declares a callable `concat`, and is no node of an imported body."""

    return node.span.path in _CONCAT_FILES.get() and not imported_node(node)


def imported_node(node: ast.Node) -> bool:
    """Whether ``node``, inside `builtin_shadows`, is a node of the body of a
    def or relationship that another module declares."""

    return node.span in _IMPORTED.get()


def copy_imported(
    original: ast.Node, copy: ast.Span, *, imported: bool = False
) -> None:
    """Inside `builtin_shadows`, keep the copy at ``copy`` of ``original`` a
    node of an imported body if ``original`` is one or, with ``imported``, it
    is a node of a relationship body another module declares."""

    nodes = _IMPORTED.get()
    if type(nodes) is set and (imported or original.span in nodes):
        nodes.add(copy)


def imported_nodes() -> frozenset[ast.Span]:
    """The nodes of imported def bodies, inside `builtin_shadows`."""

    return frozenset(_IMPORTED.get())
