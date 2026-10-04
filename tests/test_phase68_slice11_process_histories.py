"""S11 real process histories: contention, kill cuts, fork, source-free reload.

Process kill/reap is a process-crash witness only; it is not a power-loss test.
"""

import json
import os

import pytest

import _pietto_phase68_slice11_probe as probe
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_execution_template import bind_values
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return probe.compiled_template(tmp_path_factory.mktemp("s11-process"))


def prepared(tmp_path, template, jobs=1):
    workspace = w.create_workspace(str(tmp_path / "workspace"))
    identities = [
        s.register_job(workspace, template, operation=s.new_operation()).get("job")
        for _ in range(jobs)
    ]
    return workspace, identities


CLAIM_AND_HOLD = r"""
workspace = w.open_workspace(config["root"], expected_identity=config["identity"])
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
barrier("claimed %d" % publisher.epoch)
hold()
"""


def test_two_processes_contend_and_an_independent_job_progresses(tmp_path, built):
    if not probe.qualified(tmp_path):
        return
    template, _ = built
    workspace, (job, independent) = prepared(tmp_path, template, jobs=2)
    config = dict(root=workspace.root, identity=workspace.identity, job=job)
    holder = probe.child(CLAIM_AND_HOLD, config)
    try:
        probe.until(holder, "claimed 1")
        busy = s.new_operation()
        with pytest.raises(JobStoreError, match="PUBLISHER_BUSY"):
            s.claim_publisher(workspace, job, operation=busy)
        assert s.query_operation(workspace, busy) is None
        other = s.claim_publisher(workspace, independent, operation=s.new_operation())
        binding = bind_values(template, tuple((slot, 5) for slot in template.slots))
        assert (
            s.register_binding(other, binding, operation=s.new_operation()).observation
            == "COMMITTED_THIS_CALL"
        )
        other.close()
    finally:
        code, _stderr = probe.kill(holder)
    assert code == -9
    again = s.claim_publisher(workspace, job, operation=s.new_operation())
    assert again.epoch == 2
    again.close()
    # Two job registrations, the killed holder's claim, the independent claim
    # and binding, then the parent's explicit higher-epoch claim.
    assert verify_store(workspace)["operations"] == 6
    workspace.close()


CUT = r"""
workspace = w.open_workspace(config["root"], expected_identity=config["identity"])
if config["kind"] == "cancel":
    publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
real = w.commit
def cut(connection):
    # Registered child cut: before or after the actual SQLite COMMIT returns.
    if config["cut"] == "after":
        real(connection)
    barrier("cut")
    hold()
w.commit = cut
if config["kind"] == "cancel":
    s.cancel_job(publisher, operation=config["operation"])
else:
    s.claim_publisher(workspace, config["job"], operation=config["operation"])
barrier("response")
"""


@pytest.mark.parametrize("kind", ["cancel", "claim"])
@pytest.mark.parametrize("cut", ["before", "after"])
def test_kill_around_commit_has_zero_or_one_queryable_effect(
    tmp_path, built, kind, cut
):
    if not probe.qualified(tmp_path):
        return
    template, _ = built
    workspace, (job,) = prepared(tmp_path, template)
    operation = s.new_operation()
    config = dict(
        root=workspace.root,
        identity=workspace.identity,
        job=job,
        operation=operation,
        kind=kind,
        cut=cut,
    )
    worker = probe.child(CUT, config)
    try:
        probe.until(worker, "cut")
    finally:
        code, _stderr = probe.kill(worker)
    assert code == -9
    workspace.close()
    fresh = w.open_workspace(config["root"], expected_identity=config["identity"])
    try:
        queried = s.query_operation(fresh, operation)
        record = s.job_record(fresh, job)
        epoch = 1 if kind == "cancel" else 0
        if cut == "before":
            assert queried is None
            assert (record.state, record.publisher_epoch) == ("ACTIVE", epoch)
        else:
            # Exactly one committed effect is observable by a fresh query; the
            # killed caller's own response stays UNOBSERVED.
            assert queried is not None and queried.observation == "QUERIED"
            assert [o.operation for o in record.operations].count(operation) == 1
            assert (record.state, record.publisher_epoch) == (
                ("CANCELLED", 1) if kind == "cancel" else ("ACTIVE", 1)
            )
        verify_store(fresh)
        # The killed holder's lock was released by the kernel; the next owner
        # explicitly claims a higher epoch. Reissuing O under another publisher
        # is a different request.
        publisher = s.claim_publisher(fresh, job, operation=s.new_operation())
        assert publisher.epoch == record.publisher_epoch + 1
        if kind == "cancel" and cut == "after":
            with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
                s.cancel_job(publisher, operation=operation)
        elif kind == "cancel":
            assert (
                s.cancel_job(publisher, operation=operation).observation
                == "COMMITTED_THIS_CALL"
            )
        publisher.close()
        verify_store(fresh)
    finally:
        fresh.close()


CREATE_CUT = r"""
real = w.commit
def cut(connection):
    barrier("cut")
    hold()
w.commit = cut
w.create_workspace(config["root"])
"""


def test_crash_during_creation_stays_incomplete_without_cleanup(tmp_path):
    if not probe.qualified(tmp_path):
        return
    root = str(tmp_path / "workspace")
    worker = probe.child(CREATE_CUT, dict(root=root))
    try:
        probe.until(worker, "cut")
    finally:
        code, _stderr = probe.kill(worker)
    assert code == -9
    names = sorted(os.listdir(root))
    assert "CREATING" in names and "workspace.json" not in names
    with pytest.raises(JobStoreError, match="WORKSPACE_INCOMPLETE"):
        w.open_workspace(root, expected_identity=w.new_identity("ws"))
    with pytest.raises(JobStoreError, match="WORKSPACE_EXISTS"):
        w.create_workspace(root)
    assert sorted(os.listdir(root)) == names


FORK = r"""
workspace = w.open_workspace(config["root"], expected_identity=config["identity"])
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
child = os.fork()
if child == 0:
    codes = []
    for use in (publisher.use, workspace.use):
        try:
            use()
            codes.append("ACCEPTED")
        except w.JobStoreError as error:
            codes.append(str(error))
    sys.stdout.write("forked " + " ".join(codes) + "\n")
    sys.stdout.flush()
    null = os.open(os.devnull, os.O_RDWR)
    for stream in (0, 1, 2):
        os.dup2(null, stream)
    while True:
        signal.pause()
publisher.close()
barrier("closed %d" % child)
os.waitpid(child, 0)
barrier("reaped")
hold()
"""


def test_forked_handles_reject_and_inherited_lock_is_not_proven_released(
    tmp_path, built
):
    if not probe.qualified(tmp_path):
        return
    template, _ = built
    workspace, (job,) = prepared(tmp_path, template)
    config = dict(root=workspace.root, identity=workspace.identity, job=job)
    worker = probe.child(FORK, config)
    grandchild = None
    try:
        assert worker.stdout is not None
        lines = [worker.stdout.readline().split() for _ in range(2)]
        (forked,) = [x for x in lines if x[0] == "forked"]
        (line,) = [x for x in lines if x[0] == "closed"]
        grandchild = int(line[1])
        assert forked == [
            "forked",
            "PUBLISHER_FOREIGN_PROCESS",
            "WORKSPACE_FOREIGN_PROCESS",
        ]
        # The publisher descriptor was closed once, but the forked child still
        # holds the inherited open file description: the job stays locked.
        with pytest.raises(JobStoreError, match="PUBLISHER_BUSY"):
            s.claim_publisher(workspace, job, operation=s.new_operation())
        os.kill(grandchild, 9)
        probe.until(worker, "reaped")
        grandchild = None
        again = s.claim_publisher(workspace, job, operation=s.new_operation())
        assert again.epoch == 2
        again.close()
    finally:
        if grandchild is not None:
            os.kill(grandchild, 9)
        probe.kill(worker)
    verify_store(workspace)
    workspace.close()


SOURCE_FREE = r"""
import importlib
blocked = []
def forbidden(*args, **kwargs):
    raise AssertionError("source-language entry reached from a stored job")
for module_name, names in (
    ("pietto.parser_api", ("parse_source",)),
    ("pietto._project.model", ("build_empty_project_semantic_result",)),
    ("pietto._project.project_completed_semantics", ("build_project_completed_semantic_result",)),
    ("pietto._project.project_execution_template", ("_syntax_image", "_specialize")),
    ("pietto._project.discovery", ("discover_project_inputs",)),
    ("pietto._project.config", ("load_project_config", "_read_project_config_bytes")),
    ("pietto._project.trusted_source", ("_load_trusted_source",)),
):
    module = importlib.import_module(module_name)
    blocked.extend(getattr(module, name) for name in names)
for module in tuple(sys.modules.values()):
    if getattr(module, "__name__", "").startswith("pietto"):
        for name, value in tuple(vars(module).items()):
            if any(value is f for f in blocked):
                setattr(module, name, forbidden)
import pietto.ast_nodes as nodes
for value in tuple(vars(nodes).values()):
    if type(value) is type and (issubclass(value, nodes.Node) or value is nodes.Span):
        value.__new__ = forbidden
from pietto._project import project_execution as ex
from pietto._project.project_execution_postgres import PostgresExecution
workspace = w.open_workspace(config["root"], expected_identity=config["identity"])
template = s.load_job(workspace, config["job"], expected_pin=config["pin"],
    accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
binding = s.bind_record(workspace, config["job"], template, config["binding"])
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
attempt = s.open_attempt(publisher, config["generation"], binding, operation=s.new_operation())
access = ex.PostgresAccess("127.0.0.1", 9, "phase66", "pietto_query", config["password"], "disable")
premise = ex.PostgresDeploymentPremise(access, binding.artifact.request.sources, ("public", "pg_catalog"), "postgres_rows")
owner = PostgresExecution(ex.prepare_compiled_execution(binding, access, route="postgres_rows",
    postgres_deployment=premise, limits=ex.ExecutionLimits(seconds=2)))
try:
    with owner:
        for batch in owner:
            pass
except Exception:
    pass
owner.close()
s.record_attempt(publisher, attempt, owner, operation=s.new_operation())
publisher.close()
workspace.close()
print(json.dumps({
    "binding_reference": binding.instance_reference,
    "values": [[type(v).__name__, v] for v in binding.values],
    "attempt": attempt.identity,
    "helpers": sorted(n for n in sys.modules if n.startswith(("_pietto", "test_"))),
    "cwd": os.getcwd(),
}))
"""


def test_fresh_source_free_process_reloads_rebinds_and_records(tmp_path, built):
    if not probe.qualified(tmp_path):
        return
    template, build = built
    workspace, (job,) = prepared(tmp_path, template)
    publisher = s.claim_publisher(workspace, job, operation=s.new_operation())
    binding = bind_values(template, tuple((slot, 5) for slot in template.slots))
    record = s.register_binding(publisher, binding, operation=s.new_operation()).get(
        "binding"
    )
    generation = s.register_generation(
        publisher,
        record,
        binding,
        route="postgres_rows",
        isolation="stable",
        operation=s.new_operation(),
    ).get("generation")
    publisher.close()
    workspace.close()
    runtime = tmp_path / "unrelated-cwd"
    runtime.mkdir(mode=0o700)
    config = dict(
        root=workspace.root,
        identity=workspace.identity,
        job=job,
        binding=record,
        generation=generation,
        pin=build.pin,
        producer=build.producer,
        compatibility=build.compatibility,
        password=probe.SENTINEL + "-pw",
        cwd=str(runtime),
    )
    observed = json.loads(probe.finish(probe.child(SOURCE_FREE, config)))
    assert observed["helpers"] == [] and observed["cwd"] == str(runtime)
    assert observed["values"] == [["int", 5]] * len(template.slots)
    assert observed["binding_reference"] != binding.instance_reference
    fresh = w.open_workspace(config["root"], expected_identity=config["identity"])
    try:
        history = s.job_record(fresh, job)
        (attempt,) = history.attempts
        outcome = dict(attempt.outcome or ())
        assert (attempt.identity, attempt.terminal, attempt.publisher_epoch) == (
            observed["attempt"],
            "OUTCOME",
            2,
        )
        assert outcome["binding_reference"] == observed["binding_reference"]
        assert (outcome["source"], outcome["transaction"]) == ("FAILED", "NOT_STARTED")
        verify_store(fresh)
    finally:
        fresh.close()
    data = (tmp_path / "workspace" / "store.sqlite").read_bytes()
    assert config["password"].encode() not in data
