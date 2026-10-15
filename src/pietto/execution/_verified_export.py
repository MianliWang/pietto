"""D69.10 bounded, read-only verified export of one fixed saved snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pietto._project import project_job_workspace as private_workspace
from pietto._project import project_public_verified_export as composition
from pietto.execution._errors import RequestRejected, failure, workspace_failure
from pietto.execution._handle import ResultBatch, _batch
from pietto.execution._saved import _parameters
from pietto.execution._saved_read import _compatibility
from pietto.execution._workspace import WorkspaceRef

__all__ = ["VerifiedExport", "verified_export"]


@dataclass(frozen=True, slots=True)
class VerifiedExport:
    """One process-local fixed snapshot reader; exhaustion is local scope only."""

    _workspace: Any
    _acceptance: Any
    _reader: Any
    _position: int = 0
    _member: int = 0
    _offset: int = 0
    _closed: bool = False

    def __reduce_ex__(self, protocol):
        raise TypeError("VerifiedExport cannot be pickled or copied")

    def __iter__(self):
        return self

    def __next__(self) -> ResultBatch:
        if self._closed:
            raise StopIteration
        from pietto._project.project_arrow_interop import manage_batch
        from pietto._project.project_arrow_result import bind_arrow

        position, member, offset = self._position, self._member, self._offset
        if position >= self._acceptance.extent:
            self.close()
            raise StopIteration
        try:
            item = self._reader.read(member)
            batches = item.table.to_batches()
            if len(batches) != 1:
                raise RuntimeError("VERIFIED_EXPORT_BATCH")
            rows = min(
                self._acceptance.batch_rows,
                item.stop - item.start - offset,
                self._acceptance.extent - position,
            )
            managed = manage_batch(
                bind_arrow(self._reader.output.binding), batches[0].slice(offset, rows)
            )
        except Exception as caught:
            refusal = workspace_failure(caught)
            try:
                self._release()
            except Exception:
                pass
        else:
            next_position, next_member, next_offset = (
                position + rows,
                member,
                offset + rows,
            )
            if next_offset == item.stop - item.start:
                next_member, next_offset = member + 1, 0
            object.__setattr__(self, "_position", next_position)
            object.__setattr__(self, "_member", next_member)
            object.__setattr__(self, "_offset", next_offset)
            return _batch(managed)
        raise RequestRejected(refusal)

    def _release(self) -> None:
        if not self._closed:
            object.__setattr__(self, "_closed", True)
            caught = None
            try:
                self._reader.close()
            except Exception as error:
                caught = error
            try:
                self._workspace.close()
            except Exception as error:
                if caught is None:
                    caught = error
            if caught is not None:
                raise caught

    def close(self) -> None:
        try:
            self._release()
        except Exception as caught:
            refusal = workspace_failure(caught)
        else:
            return
        raise RequestRejected(refusal)

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        self.close()
        return False


def verified_export(
    workspace: WorkspaceRef,
    *,
    job: str,
    generation: str,
    checkpoint: str,
    scope: str,
    extent: int,
    purpose: str,
    route: str,
    values: tuple,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: str,
    seconds: int,
    batch_rows: int,
    parameters: dict[str, object] | None = None,
) -> VerifiedExport:
    """Open no coordinator and write no row while verifying one fixed snapshot.

    ``values`` and ``parameters`` restate the saved binding as for
    open_saved_read()."""
    if type(workspace) is not WorkspaceRef:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_REFERENCE"))
    named = _parameters(parameters)
    opened = None
    try:
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        acceptance, reader = composition.open_verified_export(
            opened,
            job=job,
            generation=generation,
            checkpoint=checkpoint,
            scope=scope,
            extent=extent,
            purpose=purpose,
            route=route,
            values=values,
            parameters=named,
            expected_pin=expected_pin,
            accepted_producer=accepted_producer,
            accepted_compatibility=_compatibility(accepted_compatibility),
            seconds=seconds,
            batch_rows=batch_rows,
        )
    except RequestRejected:
        raise
    except Exception as caught:
        try:
            if opened is not None:
                opened.close()
        except Exception:
            pass
        refusal = workspace_failure(caught)
    else:
        return VerifiedExport(opened, acceptance, reader)
    raise RequestRejected(refusal)
