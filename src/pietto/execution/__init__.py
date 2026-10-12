"""Public execution alpha: compile a project query, run it explicitly on
PostgreSQL 18.6 through the PostgreSQL rows route and read typed Arrow batches.

    query = compile_query(project, module=..., kind=..., name=...,
                          dialect="postgres", emission_contract=...)
    with execute(query, route="postgres_rows", access=PostgresAccess(...),
                 premise=PostgresDeploymentPremise(schemas=(...))) as result:
        for batch in result:
            ...

export_bundle() turns a compiled query into bytes and three trust records;
load_bundle() loads such bytes only under the records you pass, and
execute(..., values=...) binds explicit values to a bind-safe query's slots.

This is an alpha interface: names, fields and PIE-R codes may change with
documented notes. Importing it loads no database driver and no PyArrow;
compiling, exporting, loading and execute() make no connection. See
docs/execution.md.

Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED
Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED
"""

from pietto.execution._access import (
    ExecutionLimits,
    MySQLAccess,
    MySQLDeploymentPremise,
    PostgresAccess,
    PostgresDeploymentPremise,
)
from pietto.execution._errors import (
    AttemptFailed,
    CompileRejected,
    ExecutionError,
    Failure,
    HandleMisuse,
    RequestRejected,
)
from pietto.execution._handle import (
    Outcome,
    ResultBatch,
    ResultHandle,
    UnclosedHandleWarning,
    execute,
)
from pietto.execution._query import (
    CompiledQuery,
    QueryBundle,
    compile_query,
    export_bundle,
    load_bundle,
)

__all__ = [
    "AttemptFailed",
    "CompileRejected",
    "CompiledQuery",
    "ExecutionError",
    "ExecutionLimits",
    "Failure",
    "HandleMisuse",
    "MySQLAccess",
    "MySQLDeploymentPremise",
    "Outcome",
    "PostgresAccess",
    "PostgresDeploymentPremise",
    "QueryBundle",
    "RequestRejected",
    "ResultBatch",
    "ResultHandle",
    "UnclosedHandleWarning",
    "compile_query",
    "execute",
    "export_bundle",
    "load_bundle",
]
