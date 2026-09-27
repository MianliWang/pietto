"""Explicit finite ingress; checking, ownership and completion stay with S08-S10.

Raw readers must be fresh and exclusive. Before acceptance they remain with the
caller; after acceptance the returned managed stream owns deterministic cleanup.
A raw-reader lease covers all delivered backing owners, not just the handle.
"""

from __future__ import annotations

from pietto._project import project_arrow_interop as interop
from pietto._project import project_result_reader as reader

__all__: tuple[str, ...] = ()

ingest_rows = interop.build_managed_batch
ingest_batch = interop.manage_batch


def ingest_reader(
    binding,
    source,
    *,
    expected_rows,
    limits=reader.FiniteReaderLimits(),
    lease=None,
) -> interop.ManagedStream:
    return _ingest_reader(binding, source, expected_rows, limits, lease, owned=False)


def _ingest_reader(binding, source, expected_rows, limits, lease, *, owned):
    """An internally opened reader also needs cleanup before S09 acceptance."""
    try:
        captured = interop._capture(binding)
        borrowed = interop._lease_capture(lease, source, binding)
        accepted = reader.open_finite_reader(
            binding, source, expected_rows=expected_rows, limits=limits
        )
    except BaseException as primary:
        if owned:
            try:
                reader._close_source(source)
            except BaseException as cleanup:
                raise BaseExceptionGroup(
                    "owned reader acceptance and cleanup failures", [primary, cleanup]
                )
        raise
    return interop._manage_accepted_reader(accepted, captured, borrowed)
