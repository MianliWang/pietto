"""compile_query, export_bundle and load_bundle: one explicit-module project
query compiled for execution, its query bundle, and a bundle loaded under the
caller's own trust records."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re

from pietto._project import project_public_execution as composition
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_cli import _render_failure
from pietto.execution._errors import (
    CompileRejected,
    RequestRejected,
    bundle_failure,
    failure,
    request_failure,
)

__all__ = [
    "CompiledQuery",
    "QueryBundle",
    "compile_query",
    "export_bundle",
    "load_bundle",
]

_CHOICES = {
    "kind": ("table", "query"),
    "dialect": ("postgres", "mysql"),
    "literal_policy": ("preserve", "bind-safe"),
}
_RECORD = re.compile("[0-9a-f]{64}")


class CompiledQuery:
    """A verified query compiled for execution.

    Only compile_query() (``origin`` ``"live"``) and load_bundle() (``origin``
    ``"bundle"``) create one. It holds no access or premise and is never
    executed by inspecting it: repr() and the attributes only read values
    recorded when it was compiled or loaded. It is a snapshot: later edits of
    the project take effect with the next compile_query(). ``slots`` names the
    tag of each value slot, in the order execute(values=...) takes them; slot
    i is ``fixed_values[i]`` of the bind-safe ``emission``, which is the
    ``pietto.sql-emission.v1`` artifact, byte for byte what ``pietto emit-sql
    --project ... --format json`` prints for the same arguments. ``emission``
    is None for a loaded bundle, which keeps the slot order it was exported
    with.
    """

    __slots__ = (
        "_template",
        "_origin",
        "_emission",
        "_module",
        "_kind",
        "_name",
        "_dialect",
        "_release",
        "_literal_policy",
        "_slots",
    )

    def __init__(self, *arguments, **keywords):
        raise TypeError(
            "CompiledQuery objects are created by compile_query() or load_bundle()"
        )

    def __setattr__(self, name, value):
        raise AttributeError("CompiledQuery is immutable")

    def __delattr__(self, name):
        raise AttributeError("CompiledQuery is immutable")

    def __reduce_ex__(self, protocol):
        raise TypeError(
            "CompiledQuery cannot be pickled or copied; compile again or export"
            " a bundle"
        )

    @property
    def origin(self) -> str:
        return self._origin

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
    def slots(self) -> tuple[str, ...]:
        return self._slots

    @property
    def emission(self) -> bytes | None:
        return self._emission

    def __repr__(self) -> str:
        return (
            f"CompiledQuery(module={self._module!r}, kind={self._kind!r},"
            f" name={self._name!r}, dialect={self._dialect!r},"
            f" release={self._release!r}, literal_policy={self._literal_policy!r},"
            f" origin={self._origin!r})"
        )


@dataclass(frozen=True, slots=True)
class QueryBundle:
    """A compiled query as bytes, with the three records that name them.

    ``payload`` is the opaque compiled bundle; it holds the query's literal
    values and names, never an access, premise or credential. ``pin`` is the
    content identity of exactly these bytes, ``producer`` the identity of the
    project inputs and code that built them, and ``compatibility`` the
    identity of the Pietto and ANTLR runtime files installed when the query
    was compiled, which the installed code must have to load them. Each is 64
    lowercase hexadecimal characters; none is a signature or a secret, since
    each deterministically identifies the content. Keep the records in your
    own trusted records, apart from the bytes, and pass them to
    load_bundle(). repr() shows the records and the payload's length only.
    """

    payload: bytes
    pin: str
    producer: str
    compatibility: str

    def __repr__(self) -> str:
        return (
            f"QueryBundle(payload=<{len(self.payload)} bytes>, pin={self.pin!r},"
            f" producer={self.producer!r}, compatibility={self.compatibility!r})"
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
        return _compiled(outcome, template)
    raise RequestRejected(refusal)


def _compiled(outcome, template):
    emission = serialize_project_sql_emission(outcome)
    if template is None:
        text = _render_failure(json.loads(emission)).rstrip("\n")
        raise CompileRejected(outcome.status, emission, text)
    return _query(template, "live", emission)


def _query(template, origin, emission):
    query = object.__new__(CompiledQuery)
    for slot, value in zip(
        CompiledQuery.__slots__,
        (template, origin, emission, *composition.query_facts(template)),
        strict=True,
    ):
        object.__setattr__(query, slot, value)
    return query


def export_bundle(query: CompiledQuery) -> QueryBundle:
    """Return the query bundle of ``query`` and the three records that name it.

    It works for a compiled and a loaded query alike, reads no file and makes
    no connection. The same query of the same project files, contract and
    literal policy, compiled by the same installed code, gives the same
    bundle wherever the project directory is. Raises RequestRejected for a
    query that is None (PIE-R1001) or not a CompiledQuery (PIE-R1002).
    """
    if query is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_QUERY_REQUIRED"))
    if type(query) is not CompiledQuery:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_QUERY_TYPE"))
    try:
        facts = composition.export_facts(query._template)
    except Exception as caught:
        refusal = request_failure(caught)
    else:
        return QueryBundle(*facts)
    raise RequestRejected(refusal)


def load_bundle(
    payload: bytes,
    *,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: str,
) -> CompiledQuery:
    """Load exactly the bundle bytes that your own records name.

    The three records have no default and are never taken from the bytes, a
    file beside them or the environment: pass what export_bundle() returned
    when you built the bundle, kept apart from the bytes. Checks run in this
    order and the first failure is raised as RequestRejected: ``payload``,
    ``expected_pin``, ``accepted_producer`` and ``accepted_compatibility``
    are each given (PIE-R1001) and of the right type (PIE-R1002: ``bytes``,
    then 64 lowercase hexadecimal characters); the installed code is the
    code ``accepted_compatibility`` names (PIE-R1005); the bytes are at most
    32 MiB and not empty (PIE-R1002); they are the bytes ``expected_pin``
    names (PIE-R1007), except that bytes whose bracket nesting is refused
    before they are hashed are malformed (PIE-R1008) whatever the pin; they
    decode, verify and name the accepted producer and compatibility
    (PIE-R1008); the query is one that compile_query() can produce
    (PIE-R1004); it becomes an execution template (PIE-R1004, or PIE-R1005
    when the installed code changed meanwhile). Loading reads no project
    file, makes no connection and imports no driver.
    """
    if payload is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_PAYLOAD_REQUIRED"))
    if type(payload) is not bytes:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_PAYLOAD_TYPE"))
    for record in (expected_pin, accepted_producer, accepted_compatibility):
        if record is None:
            raise RequestRejected(failure("PIE-R1001", "PUBLIC_TRUST_INPUT_REQUIRED"))
        if type(record) is not str or not _RECORD.fullmatch(record):
            raise RequestRejected(failure("PIE-R1002", "PUBLIC_TRUST_INPUT_TYPE"))
    try:
        root = composition.accept_bundle(
            payload, expected_pin, accepted_producer, accepted_compatibility
        )
    except Exception as caught:
        refusal = bundle_failure(caught)
    else:
        try:
            return _query(composition.bundle_template(root), "bundle", None)
        except Exception as caught:
            refusal = request_failure(caught)
    raise RequestRejected(refusal)
