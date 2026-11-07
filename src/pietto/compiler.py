"""Public project SQL compile entry (alpha): the bytes of
``pietto emit-sql --project ... --format json`` without a subprocess.

    emission = compile_sql(project, module="models/queries.pietto",
                           kind="query", name="orders", dialect="postgres",
                           emission_contract="contract.json")
    if emission.status == "VERIFIED":
        document = json.loads(emission.document)

compile_all_sql() is the ``--all`` batch. Each call returns the status and the
exact stdout bytes of that command with the same arguments. Only a wrong
Python argument type raises TypeError; every other outcome is a returned
document, and an unexpected internal error propagates unchanged. A call reads
the project afresh, writes no file and opens no database; execution stays in
pietto.execution. See docs/spec/python-compile-api-v1.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from pietto._project.project_sql_emission_cli import EXITS, run_project_emit_sql

__all__ = ("SqlEmission", "compile_all_sql", "compile_sql")

_STATUSES = {code: status for status, code in EXITS.items()}


@dataclass(frozen=True, slots=True)
class SqlEmission:
    """One emission: ``VERIFIED``, ``BLOCKED`` or ``INPUT_REJECTED``, and the
    complete JSON document the command prints, final newline included."""

    status: str
    document: bytes


def compile_sql(
    project: str | os.PathLike[str],
    *,
    module: str,
    kind: str,
    name: str,
    dialect: str,
    emission_contract: str,
    literal_policy: str = "preserve",
) -> SqlEmission:
    """Compile one ``table`` or ``query``, as ``emit-sql --project`` does."""
    return _emit(
        project,
        module=module,
        kind=kind,
        name=name,
        dialect=dialect,
        emission_contract=emission_contract,
        literal_policy=literal_policy,
    )


def compile_all_sql(
    project: str | os.PathLike[str],
    *,
    dialect: str,
    emission_contract: str,
    module: str | None = None,
    kind: str | None = None,
    name: str | None = None,
    literal_policy: str = "preserve",
) -> SqlEmission:
    """Compile every public table and query that the given exact selectors
    match, as ``emit-sql --project ... --all`` does."""
    selectors = {"module": module, "kind": kind, "name": name}
    return _emit(
        project,
        "--all",
        **{key: value for key, value in selectors.items() if value is not None},
        dialect=dialect,
        emission_contract=emission_contract,
        literal_policy=literal_policy,
    )


def _emit(project: str | os.PathLike[str], *flags: str, **options: str) -> SqlEmission:
    root = os.fspath(project)
    if not isinstance(root, str):
        raise TypeError("project must be a str or os.PathLike[str] path")
    # The --option=value form keeps a value such as "-h", "--" or "--all" a value;
    # str.__str__ passes a str subclass as its string value, not its __format__.
    arguments = ["--project=" + str.__str__(root), *flags]
    for key, value in options.items():
        if not isinstance(value, str):
            raise TypeError(f"{key} must be a str")
        arguments.append(f"--{key.replace('_', '-')}=" + str.__str__(value))
    result = run_project_emit_sql([*arguments, "--format=json"])
    return SqlEmission(_STATUSES[result.exit_code], result.stdout)
