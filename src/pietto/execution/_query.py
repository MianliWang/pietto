"""compile_query: one explicit-module project query compiled for execution."""

from __future__ import annotations

import json
import os

from pietto._project import project_public_execution as composition
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_cli import _render_failure
from pietto.execution._errors import (
    CompileRejected,
    RequestRejected,
    failure,
    request_failure,
)

__all__ = ["CompiledQuery", "compile_query"]

_CHOICES = {
    "kind": ("table", "query"),
    "dialect": ("postgres", "mysql"),
    "literal_policy": ("preserve", "bind-safe"),
}


class CompiledQuery:
    """A verified query compiled from your project for execution.

    Only compile_query() creates one. It holds no access or premise and is
    never executed by inspecting it: repr() and the attributes only read
    values recorded when it was compiled. ``emission`` is the
    ``pietto.sql-emission.v1`` artifact, byte for byte what ``pietto emit-sql
    --project ... --format json`` prints for the same arguments.
    """

    __slots__ = (
        "_template",
        "_module",
        "_kind",
        "_name",
        "_dialect",
        "_release",
        "_literal_policy",
        "_emission",
    )

    def __init__(self, *arguments, **keywords):
        raise TypeError("CompiledQuery objects are created by compile_query()")

    def __setattr__(self, name, value):
        raise AttributeError("CompiledQuery is immutable")

    def __delattr__(self, name):
        raise AttributeError("CompiledQuery is immutable")

    def __reduce_ex__(self, protocol):
        raise TypeError("CompiledQuery cannot be pickled or copied; compile again")

    @property
    def module(self) -> str:
        return self._module

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def name(self) -> str:
        return self._name

    @property
    def dialect(self) -> str:
        return self._dialect

    @property
    def release(self) -> str:
        return self._release

    @property
    def literal_policy(self) -> str:
        return self._literal_policy

    @property
    def emission(self) -> bytes:
        return self._emission

    def __repr__(self) -> str:
        return (
            f"CompiledQuery(module={self._module!r}, kind={self._kind!r},"
            f" name={self._name!r}, dialect={self._dialect!r},"
            f" release={self._release!r}, literal_policy={self._literal_policy!r})"
        )


def _checked_arguments(project, values):
    if project is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_COMPILE_ARGUMENT"))
    if not isinstance(project, (str, os.PathLike)):
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_COMPILE_ARGUMENT"))
    for name, value in values.items():
        if value is None:
            raise RequestRejected(failure("PIE-R1001", "PUBLIC_COMPILE_ARGUMENT"))
        if type(value) is not str or value not in _CHOICES.get(name, (value,)):
            raise RequestRejected(failure("PIE-R1002", "PUBLIC_COMPILE_ARGUMENT"))


def compile_query(
    project: str | os.PathLike[str],
    *,
    module: str,
    kind: str,
    name: str,
    dialect: str,
    emission_contract: str,
    literal_policy: str = "preserve",
) -> CompiledQuery:
    """Compile one ``table`` or ``query`` of an explicit-module project.

    The arguments are those of ``pietto emit-sql --project``: the project
    root, the logical module, the declaration kind and name, the dialect
    (``postgres`` or ``mysql``), the project-relative emission contract and
    the literal policy (``preserve`` or ``bind-safe``). Compiling reads the
    project files and the installed Pietto and ANTLR runtime code; it never
    connects to a database or reads a schema.

    Raises CompileRejected with the same failure document as the command,
    or RequestRejected (PIE-R1001/R1002) for an invalid argument and
    (PIE-R1004/R1005) when a verified artifact cannot become an execution.
    """
    _checked_arguments(
        project,
        {
            "module": module,
            "kind": kind,
            "name": name,
            "dialect": dialect,
            "emission_contract": emission_contract,
            "literal_policy": literal_policy,
        },
    )
    try:
        outcome, template = composition.compile_live(
            project, module, kind, name, dialect, emission_contract, literal_policy
        )
    except Exception as caught:
        refusal = request_failure(caught)
    else:
        return _compiled(outcome, template, module, kind, name, literal_policy)
    raise RequestRejected(refusal)


def _compiled(outcome, template, module, kind, name, literal_policy):
    emission = serialize_project_sql_emission(outcome)
    if template is None:
        text = _render_failure(json.loads(emission)).rstrip("\n")
        raise CompileRejected(outcome.status, emission, text)
    query = object.__new__(CompiledQuery)
    request = template.artifact.request
    for slot, value in (
        ("_template", template),
        ("_module", module),
        ("_kind", kind),
        ("_name", name),
        ("_dialect", request.family),
        ("_release", request.release),
        ("_literal_policy", literal_policy),
        ("_emission", emission),
    ):
        object.__setattr__(query, slot, value)
    return query
