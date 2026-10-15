"""Public execution alpha: compile a project query, run it explicitly on
PostgreSQL 18.6 through the PostgreSQL rows route and read typed Arrow batches.

    query = compile_query(project, module=..., kind=..., name=...,
                          dialect="postgres", emission_contract=...)
    with execute(query, route="postgres_rows", access=PostgresAccess(...),
                 premise=PostgresDeploymentPremise(schemas=(...))) as result:
        for batch in result:
            ...

export_bundle() turns a compiled query into bytes and three trust records;
load_bundle() loads such bytes only under the records you pass,
execute(..., values=...) binds explicit values to a bind-safe query's slots,
and execute(..., parameters=...) binds a query's declared parameters by name.

This is an alpha interface: names, fields and PIE-R codes may change with
documented notes. Importing it loads no database driver, no PyArrow and no
saved-result job module, which the saved-result calls import when first
named; compiling, exporting, loading and execute() make no connection. See
docs/execution.md.

Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED
Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED
"""

from typing import TYPE_CHECKING
import importlib

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

if TYPE_CHECKING:
    from pietto.execution._inspection import (
        GenerationObservation,
        JobObservation,
        inspect_job,
    )
    from pietto.execution._publication import (
        PublicationReply,
        publish_saved_generation,
    )
    from pietto.execution._r2 import R2SourceInput, recover, save_recoverable
    from pietto.execution._reference_sink import (
        ReferenceSinkDescriptor,
        create_reference_sink,
    )
    from pietto.execution._relay import RelayCloseHandle, RelayReply, relay_live
    from pietto.execution._retirement import retire_generation
    from pietto.execution._saved import SaveCloseHandle, SaveReply, save
    from pietto.execution._saved_read import (
        SavedBatch,
        SavedRead,
        SavedReadEnd,
        new_consumer_identity,
        open_saved_read,
        release_saved_read,
    )
    from pietto.execution._verified_export import VerifiedExport, verified_export
    from pietto.execution._workspace import (
        OperationReply,
        WorkspaceRef,
        create_workspace,
        new_operation,
        open_workspace,
        operation_result,
    )

# The saved-result calls stand on the job subsystem; their owners are imported
# when one of their names is first read, so compiling and direct execution
# never load it.
_SAVED_RESULT_OWNERS = {
    "GenerationObservation": "_inspection",
    "JobObservation": "_inspection",
    "inspect_job": "_inspection",
    "PublicationReply": "_publication",
    "publish_saved_generation": "_publication",
    "R2SourceInput": "_r2",
    "recover": "_r2",
    "save_recoverable": "_r2",
    "ReferenceSinkDescriptor": "_reference_sink",
    "create_reference_sink": "_reference_sink",
    "RelayCloseHandle": "_relay",
    "RelayReply": "_relay",
    "relay_live": "_relay",
    "retire_generation": "_retirement",
    "SaveCloseHandle": "_saved",
    "SaveReply": "_saved",
    "save": "_saved",
    "SavedBatch": "_saved_read",
    "SavedRead": "_saved_read",
    "SavedReadEnd": "_saved_read",
    "new_consumer_identity": "_saved_read",
    "open_saved_read": "_saved_read",
    "release_saved_read": "_saved_read",
    "VerifiedExport": "_verified_export",
    "verified_export": "_verified_export",
    "OperationReply": "_workspace",
    "WorkspaceRef": "_workspace",
    "create_workspace": "_workspace",
    "new_operation": "_workspace",
    "open_workspace": "_workspace",
    "operation_result": "_workspace",
}


def __getattr__(name: str) -> object:
    owner = _SAVED_RESULT_OWNERS.get(name)
    if owner is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f"{__name__}.{owner}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_SAVED_RESULT_OWNERS})


__all__ = [
    "AttemptFailed",
    "CompileRejected",
    "CompiledQuery",
    "ExecutionError",
    "ExecutionLimits",
    "Failure",
    "GenerationObservation",
    "HandleMisuse",
    "JobObservation",
    "MySQLAccess",
    "MySQLDeploymentPremise",
    "OperationReply",
    "Outcome",
    "PostgresAccess",
    "PostgresDeploymentPremise",
    "PublicationReply",
    "QueryBundle",
    "R2SourceInput",
    "ReferenceSinkDescriptor",
    "RelayCloseHandle",
    "RelayReply",
    "RequestRejected",
    "ResultBatch",
    "ResultHandle",
    "SaveCloseHandle",
    "SaveReply",
    "SavedBatch",
    "SavedRead",
    "SavedReadEnd",
    "UnclosedHandleWarning",
    "VerifiedExport",
    "WorkspaceRef",
    "compile_query",
    "create_reference_sink",
    "create_workspace",
    "execute",
    "export_bundle",
    "inspect_job",
    "load_bundle",
    "new_consumer_identity",
    "new_operation",
    "open_saved_read",
    "open_workspace",
    "operation_result",
    "publish_saved_generation",
    "recover",
    "relay_live",
    "release_saved_read",
    "retire_generation",
    "save",
    "save_recoverable",
    "verified_export",
]
