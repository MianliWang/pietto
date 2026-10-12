"""Controlled target inputs and read-only evidence for public R2 recovery.

The caller owns the existing ``Resources`` lifecycle.  This module only reuses
its S06 target fixture setup, constructs public carriers in compiled-source
order, and reads the resulting durable history.  The product still opens the
native owner: source qualification, admissions, Arrow capture and recovery are
never substituted here.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True, slots=True)
class R2Fixture:
    """The four caller-held inputs for one live public R2 query."""

    query: Any
    source_requirements: tuple
    values: tuple
    trust: tuple[str, str, str]
    source: str
    source_order: tuple[tuple[str, str], ...]
    source_occurrences: int
    expected_extent: int


_CROSS_R2 = """query result:
    from rows
    cross join rows as second:
        from rows
    where rows.id > 0
    select:
        record_id = rows.id
        shifted = second.id + 1
"""


def setup_target(resource) -> tuple[dict[str, Any], ...]:
    """Install the existing immutable retained-source fixture on ``resource``."""
    target = getattr(resource, "target", None)
    if target not in ("postgres", "mysql"):
        raise ValueError("R2_TARGET_RESOURCE")
    from _pietto_phase68_slice6_probe import manager, setup

    providers = tuple(setup(resource))
    if target == "mysql":
        for table in ("threads", "events_transactions_current"):
            manager(
                resource,
                "GRANT SELECT ON performance_schema."
                + table
                + " TO 'pietto_query'@'%'",
            )
    return providers


def _source_role(target: str) -> str:
    return "pietto_query@%" if target == "mysql" else "pietto_query"


def _cross_extent(target: str) -> int:
    """The fixed fixture rows under the first CROSS input's ``id > 0`` filter."""
    from _pietto_target_conformance_cases import emission_rows

    rows = emission_rows(target)
    if len(rows) != 4 or any(item[1]["kind"] != "int" for item in rows):
        raise ValueError("R2_CROSS_FIXTURE_ROWS")
    return sum(int(item[1]["value"]) > 0 for item in rows) * len(rows)


def live_r2(directory, providers, *, target: str = "postgres") -> R2Fixture:
    """Build the live query and its exact public source declarations.

    ``providers`` comes from :func:`setup_target`; names are matched only
    against this query's own sources, in its immutable compiled order.
    """
    from _pietto_phase66_sql_emission_probe import CONFIG, source_files
    from _pietto_phase68_slice6_cases import fixture
    from pietto.execution import R2SourceInput, compile_query

    project = Path(directory) / "public-r2"
    if target not in ("postgres", "mysql"):
        raise ValueError("R2_TARGET")
    item = fixture(target, "R2_bound", "values")
    header, marker, _body = item["source"].partition("query result:\n")
    if marker != "query result:\n":
        raise ValueError("R2_CROSS_SOURCE")
    source_text = header + _CROSS_R2
    project.mkdir(parents=True)
    (project / "pietto.toml").write_text(CONFIG, encoding="utf-8")
    for name, content in sorted(source_files(source_text).items()):
        (project / name).write_text(content, encoding="utf-8")
    (project / "contract.json").write_text(item["contract"], encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="result",
        dialect=target,
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )
    by_source = {(item["namespace"], item["name"]): item for item in providers}
    template = cast(Any, query)._template
    sources = template.artifact.request.sources
    if len(by_source) != len(providers):
        raise ValueError("FIXTURE_PROVIDER_DUPLICATE")
    source_order = tuple((source.namespace, source.name) for source in sources)
    occurrences = source_text.count("from rows\n")
    if len(source_order) != 1 or source_order[0] not in by_source or occurrences != 2:
        raise ValueError("R2_CROSS_SOURCE_ORDER")
    requirements = []
    for source in sources:
        provider = by_source.get((source.namespace, source.name))
        if provider is None:
            raise ValueError("FIXTURE_PROVIDER_SOURCE")
        requirements.append(
            R2SourceInput(
                source.namespace,
                source.name,
                provider["provider"],
                provider["version"],
                provider["revision"],
                provider["namespace"],
                provider["registry"],
                provider["definition"],
                tuple(provider["tokens"]),
                _source_role(target),
                "Owned fixture: immutable token/payload and complete visible "
                "domain; version retained until explicit target cleanup.",
            )
        )
    root = template.artifact.request.verification.completed.root
    values = tuple(slot.original.site.position.literal.value for slot in template.slots)
    if values != (0, 1):
        raise ValueError("R2_CROSS_VALUES")
    extent = _cross_extent(target)
    if extent != 12:
        raise ValueError("R2_CROSS_EXTENT")
    return R2Fixture(
        query,
        tuple(requirements),
        values,
        (
            root.expected_pin,
            root.accepted_producer,
            root.accepted_compatibility[-1],
        ),
        source_text,
        source_order,
        occurrences,
        extent,
    )


def target_inputs(resource):
    """Public per-call access and premise for one already prepared target."""
    target = getattr(resource, "target", None)
    if target == "postgres":
        from pietto.execution import PostgresAccess, PostgresDeploymentPremise

        return (
            PostgresAccess(
                "127.0.0.1",
                resource.port,
                "phase66",
                "pietto_query",
                resource._passwords[1],
                "disable",
            ),
            PostgresDeploymentPremise(("public", "pg_catalog")),
        )
    if target == "mysql":
        from pietto.execution import MySQLAccess, MySQLDeploymentPremise

        return (
            MySQLAccess(
                "localhost",
                resource.port,
                "phase66",
                "pietto_query",
                resource._passwords[1],
                str(resource.ca_path),
                _source_role(target),
            ),
            MySQLDeploymentPremise(("phase66",)),
        )
    raise ValueError("R2_TARGET_RESOURCE")


def setup_postgres(resource) -> tuple[dict[str, Any], ...]:
    """Compatibility spelling for the original PostgreSQL-only caller."""
    if getattr(resource, "target", None) != "postgres":
        raise ValueError("POSTGRES_RESOURCE")
    return setup_target(resource)


def postgres_inputs(resource):
    """Compatibility spelling for the original PostgreSQL-only caller."""
    if getattr(resource, "target", None) != "postgres":
        raise ValueError("POSTGRES_RESOURCE")
    return target_inputs(resource)


def prefix_limits():
    """Capture eight data rows after bounded admission metadata."""
    from pietto.execution import ExecutionLimits

    return ExecutionLimits(batch_rows=2, max_rows=8, seconds=60)


def recovery_limits():
    """The fresh recovery attempt has room to enumerate all nine cross rows."""
    from pietto.execution import ExecutionLimits

    return ExecutionLimits(batch_rows=3, max_rows=64, seconds=60)


def run_public_r2_native_case(directory, resource):
    """One explicit acquired PostgreSQL R2 save/recover/replay witness.

    The caller owns the qualified resource acquisition and cleanup.  This is
    intentionally not collected by ordinary pytest: it needs pinned Arrow and
    a real PostgreSQL service.
    """
    from pietto.execution import (
        R2SourceInput,
        RequestRejected,
        SavedReadEnd,
        create_workspace,
        inspect_job,
        new_operation,
        new_consumer_identity,
        open_saved_read,
        operation_result,
        recover,
        save_recoverable,
        verified_export,
    )
    from pietto._project import project_job_capture as capture
    from pietto._project import project_job_workspace as private_workspace
    from pietto._project.project_job_workspace import read, write

    fixture = live_r2(Path(directory) / "bound", setup_postgres(resource))
    access, premise = postgres_inputs(resource)
    workspace = create_workspace(
        Path(directory) / "workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    saved = save_recoverable(
        workspace,
        fixture.query,
        source_requirements=fixture.source_requirements,
        operation=new_operation(),
        route="postgres_rows",
        access=access,
        premise=premise,
        limits=prefix_limits(),
        values=fixture.values,
    )
    if saved.terminal != "FAILED" or saved.cleanup is not None:
        raise AssertionError("R2_CAPTURE_PREFIX")
    if saved.job is None or saved.generation is None:
        raise AssertionError("R2_CAPTURE_IDENTITY")
    opened = private_workspace.open_workspace(
        workspace.root, expected_identity=workspace.identity
    )
    try:
        checkpoint = capture.checkpoint_snapshot(
            opened, saved.job, saved.generation
        ).checkpoint
    finally:
        opened.close()
    operation = new_operation()
    recovered = recover(
        workspace,
        job=saved.job,
        generation=saved.generation,
        checkpoint=checkpoint,
        query=fixture.query,
        source_requirements=fixture.source_requirements,
        operation=operation,
        route="postgres_rows",
        access=access,
        premise=premise,
        limits=recovery_limits(),
        expected_pin=fixture.trust[0],
        accepted_producer=fixture.trust[1],
        accepted_compatibility=fixture.trust[2],
        purpose="public-r2-recovery",
        seconds=60,
        values=fixture.values,
    )
    if recovered.terminal != "COMPLETED" or recovered.cleanup is not None:
        raise AssertionError("R2_RECOVERY")
    trace = recovery_trace(workspace, saved.job, saved.generation)
    recorded = operation_result(workspace, operation)
    if recorded is None or trace["continuation_sequence"] != recorded.sequence:
        raise AssertionError("R2_RECOVERY_OPERATION")
    before = trace["operations"]
    replay = recover(
        workspace,
        job=saved.job,
        generation=saved.generation,
        checkpoint=checkpoint,
        query=fixture.query,
        source_requirements=fixture.source_requirements,
        operation=operation,
        route="postgres_rows",
        access=access,
        premise=premise,
        limits=recovery_limits(),
        expected_pin=fixture.trust[0],
        accepted_producer=fixture.trust[1],
        accepted_compatibility=fixture.trust[2],
        purpose="public-r2-recovery",
        seconds=60,
        values=fixture.values,
    )
    if replay.terminal != "REPLY_LOST_OR_PARTIAL" or (
        recovery_trace(workspace, saved.job, saved.generation)["operations"] != before
    ):
        raise AssertionError("R2_RECOVERY_REPLAY")
    changed = (
        ("job", "job-" + "0" * 32),
        ("generation", "gen-" + "0" * 32),
        ("checkpoint", None),
        ("values", fixture.values[:-1] + ("changed",)),
        (
            "source_requirements",
            (
                R2SourceInput(
                    fixture.source_requirements[0].namespace,
                    fixture.source_requirements[0].name,
                    "changed-provider",
                    fixture.source_requirements[0].version,
                    fixture.source_requirements[0].revision,
                    fixture.source_requirements[0].registry_namespace,
                    fixture.source_requirements[0].registry_name,
                    fixture.source_requirements[0].definition,
                    fixture.source_requirements[0].token_columns,
                    fixture.source_requirements[0].role,
                    fixture.source_requirements[0].provider_guarantee,
                ),
                *fixture.source_requirements[1:],
            ),
        ),
    )
    for name, value in changed:
        arguments = {
            "job": saved.job,
            "generation": saved.generation,
            "checkpoint": checkpoint,
            "query": fixture.query,
            "source_requirements": fixture.source_requirements,
            "operation": operation,
            "route": "postgres_rows",
            "access": access,
            "premise": premise,
            "limits": recovery_limits(),
            "expected_pin": fixture.trust[0],
            "accepted_producer": fixture.trust[1],
            "accepted_compatibility": fixture.trust[2],
            "purpose": "public-r2-recovery",
            "seconds": 60,
            "values": fixture.values,
        }
        arguments[name] = value
        try:
            recover(workspace, **arguments)
        except RequestRejected:
            pass
        else:
            raise AssertionError("R2_RECOVERY_REPLAY_" + name.upper())
        if (
            recovery_trace(workspace, saved.job, saved.generation)["operations"]
            != before
        ):
            raise AssertionError("R2_RECOVERY_REPLAY_WRITE_" + name.upper())
    observed = inspect_job(workspace, job=saved.job)
    generation = next(
        (item for item in observed.generations if item.identity == saved.generation),
        None,
    )
    if generation is None or generation.checkpoint is None or not generation.closings:
        raise AssertionError("R2_INSPECTION")
    common = {
        "job": saved.job,
        "generation": saved.generation,
        "checkpoint": generation.checkpoint,
        "expected_pin": fixture.trust[0],
        "accepted_producer": fixture.trust[1],
        "accepted_compatibility": fixture.trust[2],
        "values": fixture.values,
        "scope": "complete_capture",
        "extent": generation.frontier,
        "purpose": "public-r2-read",
        "route": "postgres_rows",
        "batch_rows": 3,
        "seconds": 60,
    }

    def operations():
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            return read(
                opened,
                lambda c: c.execute(
                    "SELECT count(*) FROM operation WHERE job = ?", (saved.job,)
                ).fetchone()[0],
            )
        finally:
            opened.close()

    def refuses_reader(**changes):
        before = operations()
        try:
            open_saved_read(
                workspace,
                **(common | changes),
                consumer=new_consumer_identity(),
                register_operation=new_operation(),
                open_operation=new_operation(),
            )
        except RequestRejected:
            pass
        else:
            raise AssertionError("R2_SAVED_READ_REFUSAL")
        if operations() != before:
            raise AssertionError("R2_SAVED_READ_WRITE")

    refuses_reader(expected_pin="0" * 64)
    refuses_reader(values=tuple(value + 1 for value in fixture.values))

    def changed_reader_row(table, column, value):
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            original = read(
                opened,
                lambda c: c.execute(
                    "SELECT " + column + " FROM " + table + " WHERE generation = ?",
                    (saved.generation,),
                ).fetchone()[0],
            )
            write(
                opened,
                lambda c: c.execute(
                    "UPDATE "
                    + table
                    + " SET "
                    + column
                    + " = ?"
                    + " WHERE generation = ?",
                    (value, saved.generation),
                ),
            )
            return original
        finally:
            opened.close()

    def restore_reader_row(table, column, value):
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            write(
                opened,
                lambda c: c.execute(
                    "UPDATE "
                    + table
                    + " SET "
                    + column
                    + " = ?"
                    + " WHERE generation = ?",
                    (value, saved.generation),
                ),
            )
        finally:
            opened.close()

    opened = private_workspace.open_workspace(
        workspace.root, expected_identity=workspace.identity
    )
    try:
        specification = read(
            opened,
            lambda c: c.execute(
                "SELECT specification FROM extraction WHERE generation = ?",
                (saved.generation,),
            ).fetchone()[0],
        )
    finally:
        opened.close()
    changed_specification = json.loads(specification)
    changed_specification["sources"][0][2] = "changed-provider"
    original = changed_reader_row(
        "extraction",
        "specification",
        json.dumps(changed_specification, sort_keys=True, separators=(",", ":")),
    )
    try:
        refuses_reader()
    finally:
        restore_reader_row("extraction", "specification", original)
    for column, value in (("contract", "0" * 64), ("scheme", "null")):
        original = changed_reader_row("capture", column, value)
        try:
            refuses_reader()
        finally:
            restore_reader_row("capture", column, original)

    export_common = common
    opened = private_workspace.open_workspace(
        workspace.root, expected_identity=workspace.identity
    )
    try:
        member = capture.checkpoint_snapshot(
            opened, saved.job, saved.generation, checkpoint=generation.checkpoint
        ).members[0]
        member_path = Path(opened.root) / "chunks" / member.file
        missing_path = member_path.with_suffix(".missing")
        member_path.rename(missing_path)
    finally:
        opened.close()
    before = operations()
    try:
        with verified_export(workspace, **export_common) as exported:
            next(exported)
    except RequestRejected:
        pass
    else:
        raise AssertionError("R2_VERIFIED_EXPORT_MEMBER")
    finally:
        missing_path.rename(member_path)
    if operations() != before:
        raise AssertionError("R2_VERIFIED_EXPORT_WRITE")

    rows = 0
    consumer = new_consumer_identity()
    first = open_saved_read(
        workspace,
        **common,
        consumer=consumer,
        register_operation=new_operation(),
        open_operation=new_operation(),
    )
    try:
        offered = first.next(3, operation=new_operation())
        if isinstance(offered, SavedReadEnd):
            raise AssertionError("R2_SAVED_READ_EMPTY")
        first_range, first_delivery = (offered.start, offered.stop), offered.delivery
        offered.batch.close()
    finally:
        first.close()
    with open_saved_read(
        workspace,
        **common,
        consumer=consumer,
        register_operation=None,
        open_operation=new_operation(),
    ) as reader:
        while True:
            item = reader.next(3, operation=new_operation())
            if isinstance(item, SavedReadEnd):
                break
            if rows == 0 and (
                (item.start, item.stop) != first_range
                or item.delivery == first_delivery
            ):
                raise AssertionError("R2_SAVED_READ_REISSUE")
            rows += item.stop - item.start
            item.batch.close()
            reader.ack(item, operation=new_operation())
    if rows != generation.frontier:
        raise AssertionError("R2_SAVED_READ")
    exported_rows = 0
    with verified_export(workspace, **export_common) as exported:
        for item in exported:
            exported_rows += item.num_rows
            item.close()
    if exported_rows != generation.frontier:
        raise AssertionError("R2_VERIFIED_EXPORT")
    return workspace, fixture, saved, recovered


def recovery_trace(workspace_ref, job, generation) -> dict[str, Any]:
    """Read durable R2 ordering facts after public save/recover calls.

    The initial qualification is atomically recorded with ``begin_extraction``
    before any chunk publication.  A continuation can publish only after its
    ``reconcile_extraction`` operation, which follows its full saved-prefix
    comparison.  This helper reads those facts; it does not drive them.
    """
    from pietto._project import project_job_store as store
    from pietto._project import project_job_workspace as private_workspace
    from pietto._project.project_job_workspace import read

    opened = private_workspace.open_workspace(
        workspace_ref.root, expected_identity=workspace_ref.identity
    )
    try:
        history = store.job_record(opened, job)

        def facts(connection):
            extraction = connection.execute(
                "SELECT attempt,qualification FROM extraction"
                " WHERE generation=? AND job=?",
                (generation, job),
            ).fetchone()
            continuations = connection.execute(
                "SELECT attempt,predecessor,frontier,reach,rows FROM continuation"
                " WHERE generation=? AND job=? ORDER BY attempt",
                (generation, job),
            ).fetchall()
            reconciled = connection.execute(
                "SELECT attempt,position,matched FROM reconciliation"
                " WHERE attempt IN (SELECT attempt FROM continuation"
                " WHERE generation=? AND job=?) ORDER BY attempt",
                (generation, job),
            ).fetchall()
            chunks = connection.execute(
                "SELECT attempt,start,stop FROM chunk WHERE generation=?"
                " ORDER BY start,attempt",
                (generation,),
            ).fetchall()
            operations = connection.execute(
                "SELECT sequence,kind,request FROM operation WHERE job=?"
                " ORDER BY sequence",
                (job,),
            ).fetchall()
            return extraction, continuations, reconciled, chunks, operations

        extraction, continuations, reconciled, chunks, stored_operations = read(
            opened, facts
        )
    finally:
        opened.close()
    if extraction is None or not extraction[1]:
        raise AssertionError("R2 qualification was not stored with extraction")
    operations = tuple((item.sequence, item.kind) for item in history.operations)
    begun = tuple(
        sequence for sequence, kind in operations if kind == "begin_extraction"
    )
    published = tuple(
        sequence for sequence, kind in operations if kind == "publish_chunk"
    )
    if len(begun) != 1 or (published and begun[0] >= published[0]):
        raise AssertionError("R2 qualification did not precede first chunk")
    continued = tuple(
        sequence for sequence, kind in operations if kind == "begin_continuation"
    )
    barriers = tuple(
        sequence for sequence, kind in operations if kind == "reconcile_extraction"
    )
    if continuations and (len(continued) != 1 or len(barriers) != 1):
        raise AssertionError("R2 continuation lacks one committed comparison barrier")
    requests = {
        sequence: json.loads(request) for sequence, _kind, request in stored_operations
    }
    initial_publishes = tuple(
        sequence
        for sequence, kind in operations
        if kind == "publish_chunk" and requests[sequence]["attempt"] == extraction[0]
    )
    if not initial_publishes or begun[0] >= initial_publishes[0]:
        raise AssertionError("R2 first capture lacks qualified committed prefix")
    if continuations:
        attempt, _predecessor, _frontier, reach, rows = continuations[0]
        matched = tuple(row for row in reconciled if row[0] == attempt)
        continuation_publishes = tuple(
            sequence
            for sequence, kind in operations
            if kind == "publish_chunk" and requests[sequence]["attempt"] == attempt
        )
        if (
            len(matched) != 1
            or matched[0][1] < reach
            or matched[0][2] != rows
            or not continuation_publishes
            or barriers[0] >= continuation_publishes[0]
        ):
            raise AssertionError("R2 comparison did not precede continuation commit")
    return {
        "operations": operations,
        "qualification": json.loads(extraction[1]),
        "initial_attempt": extraction[0],
        "continuations": tuple(tuple(row) for row in continuations),
        "reconciliations": tuple(tuple(row) for row in reconciled),
        "chunks": tuple(tuple(row) for row in chunks),
        "first_qualification_sequence": begun[0],
        "first_chunk_sequence": None if not published else published[0],
        "continuation_sequence": None if not continued else continued[0],
        "comparison_sequence": None if not barriers else barriers[0],
    }
