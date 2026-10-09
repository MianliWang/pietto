"""Call-scoped verification: inside one top-level call each exact object is
verified completely once, every new call verifies again, failures are never
remembered, and the hot verifier loops grow linearly. Runs are counted with
sys.monitoring on the unchanged verifier bodies; there is no production hook.
Pure; no database or Arrow."""

from __future__ import annotations

import ast
from collections import Counter
import dataclasses
from pathlib import Path
import sys
import threading
from typing import Any, cast

import pytest

from _pietto_phase68_slice4_probe import template
from pietto._project import model
from pietto._project import project_compiled_verification as compiled_verification
from pietto._project import project_completed_semantics as completed_semantics
from pietto._project import project_execution as execution
from pietto._project import project_guard_preparation as guard_preparation
from pietto._project import project_query_block_ir_verification as ir_verification
from pietto._project import project_sql_plan_requirements as requirements
from pietto._project import project_sql_plan_verification as plan_verification
from pietto._project.project_compiled_build import build_compiled
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_lowering import emit_compiled
from pietto._project.project_execution_template import (
    bind_values,
    prepare_compiled_template,
)

ROOT = Path(__file__).resolve().parents[1]
MON = sys.monitoring


def _body(module, private, public):
    """The complete check: the memo's private body, else today's public one."""
    return getattr(module, private, None) or getattr(module, public)


# The complete bodies this guard counts: the seven memoized structural checks
# plus the description and semantics checks they call. The binding-layer
# verifiers are not memoized; their nested compiled checks are memo hits.
BODIES = {
    "verify(root)": getattr(model, "_verify_compiled_input", None)
    or model.CompiledProjectInput.verify,
    "verify_description": compiled_verification.verify_description,
    "verify_compiled_semantics": completed_semantics.verify_compiled_semantics,
    "verify_compiled_query_block_ir": _body(
        ir_verification,
        "_verify_compiled_query_block_ir",
        "verify_compiled_query_block_ir",
    ),
    "verify_compiled_sql_plan": _body(
        plan_verification, "_verify_compiled_sql_plan", "verify_compiled_sql_plan"
    ),
    "verify_compiled_emission": _body(
        compiled_verification,
        "_verify_compiled_emission",
        "verify_compiled_emission",
    ),
    "verify_compiled_requirement_report": _body(
        requirements,
        "_verify_compiled_requirement_report",
        "verify_compiled_requirement_report",
    ),
    "verify_scope": _body(guard_preparation, "_verify_scope", "verify_scope"),
    "verify_preparation": _body(
        guard_preparation, "_verify_preparation", "verify_preparation"
    ),
}


class Runs:
    """Runs of the counted bodies per (body, argument identities, thread)."""

    def __init__(self):
        self.names = {f.__code__: n for n, f in BODIES.items()}
        self.runs: Counter = Counter()
        self.label: dict[int, str] = {}
        self.held: list = []
        self.paths: dict = {}
        self.errors: list[str] = []

    def count(self, name, *subjects):
        return self.runs[(name, tuple(map(id, subjects)), threading.get_ident())]

    def _start(self, code, offset):
        try:  # never raise into product code
            frame = sys._getframe(1)
            names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
            args = tuple(frame.f_locals[n] for n in names)
            self.held.append(args)  # no id reuse inside the block
            for value in args:
                self.label.setdefault(
                    id(value), "#%d %s" % (len(self.label), type(value).__name__)
                )
            key = (self.names[code], tuple(map(id, args)), threading.get_ident())
            self.runs[key] += 1
            if self.runs[key] > 1:
                path, caller = [], frame.f_back
                while caller is not None and len(path) < 12:
                    module = caller.f_globals.get("__name__", "")
                    if module.startswith("pietto.") and not module.endswith(
                        "project_verification_scope"
                    ):
                        path.append(caller.f_code.co_qualname)
                    caller = caller.f_back
                self.paths.setdefault(key, []).append(" > ".join(reversed(path)))
        except Exception as error:
            self.errors.append(repr(error))

    def __enter__(self):
        free = [i for i in range(6) if MON.get_tool(i) is None]
        assert free, "no free sys.monitoring tool id"
        self.tool = free[-1]
        MON.use_tool_id(self.tool, "pietto-verification-budget")
        MON.register_callback(self.tool, MON.events.PY_START, self._start)
        for code in self.names:
            MON.set_local_events(self.tool, code, MON.events.PY_START)
        return self

    def __exit__(self, *exc):
        for code in self.names:
            MON.set_local_events(self.tool, code, 0)
        MON.register_callback(self.tool, MON.events.PY_START, None)
        MON.free_tool_id(self.tool)

    def report(self, route, allowed):
        lines = []
        for key, n in sorted(self.runs.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            name, ids, _thread = key
            budget = allowed.get(name, 1)
            if n > budget:
                subjects = ", ".join(self.label.get(i, "?") for i in ids)
                lines.append(
                    "  %s(%s): %d runs, budget %d" % (name, subjects, n, budget)
                )
                for path in self.paths.get(key, [])[:3]:
                    lines.append("    repeat via " + path)
        if lines or self.errors:
            return (
                "verification budget [%s]: each exact object is verified once per "
                "top-level call\n"
                % route
                + "\n".join(lines + self.errors)
                + "\nRoute the nested check through the call-scoped memo, or add a "
                "reasoned allowance."
            )
        return None


@pytest.fixture(scope="module")
def ordinary(tmp_path_factory):
    original = template(tmp_path_factory.mktemp("verification-scope-source"))
    built = build_compiled(original.artifact)
    values = tuple(v.value for v in original.artifact.fixed_values)
    return original, built, values


@pytest.fixture(scope="module")
def guarded(tmp_path_factory):
    """The refined guarded case with the most requirement origins, compiled."""
    from _pietto_phase68_slice7_cases import case_preparation, manifest
    from test_phase68_slice6_refinement import capabilities

    from pietto._project.project_guard_preparation import prepare_guarded_output
    from pietto._project.project_refinement import TieRefinement, prepare_refinement

    case = next(c for c in manifest() if c["name"] == "refined_tied_subject")
    original = case_preparation(
        tmp_path_factory.mktemp("verification-scope-guard"), "postgres", case
    )
    refinement = prepare_refinement(
        original.artifact,
        capabilities(original.artifact),
        policy=TieRefinement(),
        output=prepare_guarded_output(original),
    )
    built = build_compiled(original.artifact, guarded=original, refinement=refinement)
    return original, built, tuple(v.value for v in original.artifact.fixed_values)


def _load(built):
    return load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )


def _access():
    return execution.PostgresAccess(
        "127.0.0.1", 5432, "phase66", "pietto_query", "unused-fixture", "disable"
    )


def _route(name, world):
    """(call, required objects named by display name, allowances) for one route.
    Every route loads its own fresh root, outside the counted calls."""
    original, built, values = world
    root = _load(built)
    if name == "prepare":
        return (lambda: prepare_compiled_template(root)), [("verify(root)", root)], {}
    if name == "bind":
        loaded = prepare_compiled_template(root)
        pairs = tuple((slot, 2) for slot in loaded.slots)
        return (
            (lambda: bind_values(loaded, pairs)),
            [("verify(root)", root)],
            {},
        )
    if name == "lower":
        return (lambda: emit_compiled(root, values)), [("verify(root)", root)], {}
    if name == "inspect":
        from pietto._project.project_sql_emission_inspection import (
            inspect_project_sql_emission,
        )

        artifact = emit_compiled(root, values)
        return (
            lambda: inspect_project_sql_emission(artifact, artifact.request),
            [("verify(root)", root)],
            {},
        )
    if name in ("describe", "compatible"):
        from pietto._project.project_execution_template import (
            compatible_compiled_values,
            describe_compiled_binding,
        )

        loaded = prepare_compiled_template(root)
        left, right = (
            bind_values(loaded, tuple((slot, 2) for slot in loaded.slots))
            for _ in range(2)
        )
        if name == "describe":
            return (
                lambda: describe_compiled_binding(left, route="postgres_rows"),
                [("verify(root)", root)],
                {},
            )
        return (
            lambda: compatible_compiled_values(left, right, route="postgres_rows"),
            [("verify(root)", root)],
            {},
        )
    if name == "live":
        from pietto._project.project_execution_template import prepare_live_template

        # Building a root runs the complete description check four times on the
        # one built Description: the export check, the pre-pin check, the
        # CompiledProjectInput constructor and its first verify(); never memoized.
        return (
            lambda: prepare_live_template(original.artifact),
            [],
            {"verify_description": 4},
        )
    if name in GUARDED_ROUTES:
        return _guarded_route(name, root, values), [("verify(root)", root)], {}
    if name == "execution":
        loaded = prepare_compiled_template(root)
        binding = bind_values(loaded, tuple((slot, 2) for slot in loaded.slots))
        access = _access()
        premise = execution.PostgresDeploymentPremise(
            access,
            binding.artifact.request.sources,
            ("public", "pg_catalog"),
            "postgres_rows",
        )
        return (
            lambda: execution.prepare_compiled_execution(
                binding, access, route="postgres_rows", postgres_deployment=premise
            ),
            [("verify(root)", root)],
            {},
        )
    raise AssertionError(name)


def _guarded_route(name, root, values):
    """One public call of the compiled guarded and refined chain; everything it
    consumes is built outside the counted call."""
    from pietto._project.project_guard_preparation import (
        prepare_compiled_guarded,
        prepare_guarded_template,
    )
    from pietto._project.project_guard_program import prepare_program, statement_for
    from pietto._project.project_guard_rendering import render_guard
    from pietto._project.project_guard_verification import verify_native_guard
    from pietto._project.project_refinement import prepare_compiled_refinement

    artifact = emit_compiled(root, values)
    candidate = prepare_compiled_guarded(artifact)
    if name == "guarded":
        return lambda: prepare_compiled_guarded(artifact)
    if name == "guarded_template":
        return lambda: prepare_guarded_template(candidate)
    template = prepare_guarded_template(candidate)
    rebound = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    if name == "refinement":
        return lambda: prepare_compiled_refinement(
            rebound.artifact, binding=rebound, guarded=rebound.guarded
        )
    refined = prepare_compiled_refinement(
        rebound.artifact, binding=rebound, guarded=rebound.guarded
    )
    if name == "program":
        return lambda: prepare_program(
            rebound.guarded, binding=rebound, refinement=refined
        )
    program = prepare_program(rebound.guarded, binding=rebound, refinement=refined)
    if name == "statement":
        return lambda: statement_for(program, "guard")
    statement = statement_for(program, "guard")
    if name == "render":
        return lambda: render_guard(statement)
    native = render_guard(statement)
    assert name == "native_guard", name
    return lambda: verify_native_guard(native)


GUARDED_ROUTES = (
    "guarded",
    "guarded_template",
    "refinement",
    "program",
    "statement",
    "render",
    "native_guard",
)
ROUTES = (
    "prepare",
    "bind",
    "lower",
    "inspect",
    "execution",
    "describe",
    "compatible",
    "live",
    *GUARDED_ROUTES,
)
# Reached only inside an execution owner's attempt, which needs a live database;
# the native campaign exercises it.
OWNER_ONLY = {"verify_native"}


def _world(request, route):
    return request.getfixturevalue("guarded" if route in GUARDED_ROUTES else "ordinary")


@pytest.mark.parametrize("route", ROUTES)
def test_each_exact_object_is_verified_once_per_top_level_call(request, route):
    call, required, allowed = _route(route, _world(request, route))
    for attempt in range(2):
        with Runs() as runs:
            result = call()
        message = runs.report(route, allowed)
        assert message is None, message
        if route == "live":
            # The root is built inside the call: exactly one root check and the
            # four description checks of building it.
            root = cast(Any, result).artifact.request.verification.completed.root
            required = [("verify(root)", root)]
            assert runs.count("verify_description", root.description) == 4
        for name, subject in required:
            assert runs.count(name, subject) == 1, (route, attempt, name)


class _ShadowScope(dict):
    """A scope whose every hit also re-runs the complete check it skips."""

    def __init__(self, audit):
        super().__init__()
        self.audit = audit

    def __contains__(self, key):
        if not dict.__contains__(self, key):
            return False
        self.audit.hits += 1
        try:
            key[0](*self[key])
        except Exception as error:
            self.audit.divergences.append((key[0].__qualname__, repr(error)))
        return True


class _Shadow(threading.local):
    def __init__(self):
        self.hits, self.divergences, self._scope = 0, [], None

    @property
    def scope(self):
        return self._scope

    @scope.setter
    def scope(self, value):
        self._scope = _ShadowScope(self) if type(value) is dict else value


@pytest.mark.parametrize("route", ROUTES)
def test_memo_hits_never_hide_a_failure(request, route, monkeypatch):
    """Every check a hit skips would have passed: the route's own work never
    changes an object it already verified inside the call."""
    from pietto._project import project_verification_scope as scope

    call = _route(route, _world(request, route))[0]
    expected = call()
    shadow = _Shadow()
    monkeypatch.setattr(scope, "_local", shadow)
    observed = call()
    monkeypatch.undo()
    assert shadow.hits and shadow.divergences == []
    if route == "lower":
        from pietto._project.project_sql_emission import CompiledEmissionArtifact

        assert isinstance(expected, CompiledEmissionArtifact)
        assert isinstance(observed, CompiledEmissionArtifact)
        assert observed.rendered.sql == expected.rendered.sql


def test_equal_but_distinct_roots_are_each_verified(ordinary):
    from pietto._project.project_verification_scope import entry

    _original, built, _values = ordinary
    first, second = _load(built), _load(built)
    assert first.description == second.description
    assert first.description is not second.description

    @entry
    def both():
        first.verify()
        second.verify()

    with Runs() as runs:
        both()
    assert runs.count("verify(root)", first) == runs.count("verify(root)", second) == 1


def _swap(description, group, index, replacement):
    members = description.members
    name, records = members[group]
    changed = (*records[:index], replacement, *records[index + 1 :])
    object.__setattr__(
        description,
        "members",
        (*members[:group], (name, changed), *members[group + 1 :]),
    )
    return members


@pytest.mark.parametrize("change", ("content", "record_identity"))
def test_change_between_calls_reports_the_exact_first_failure(ordinary, change):
    from pietto._project.project_compiled_schema import CompiledError

    _original, built, _values = ordinary
    root = _load(built)
    root.verify()
    description = root.description
    group = next(i for i, (_, records) in enumerate(description.members) if records)
    victim = description.members[group][1][0]
    if change == "content":
        replacement = dataclasses.replace(
            victim, values=(*victim.values[:-1], object())
        )
    else:
        replacement = dataclasses.replace(victim)
    original = _swap(description, group, 0, replacement)
    try:
        with pytest.raises(CompiledError) as refused:
            root.verify()
    finally:
        object.__setattr__(description, "members", original)
    expected = {
        "content": "COMPILED_VALUE",
        "record_identity": "COMPILED_INPUT_CHANGED",
    }
    assert str(refused.value) == expected[change]
    root.verify()


def test_marks_record_success_only_and_results_stay_fresh(ordinary):
    from pietto._project.project_verification_scope import entry, once

    _original, built, values = ordinary
    root = _load(built)
    artifact = emit_compiled(root, values)
    plan = artifact.request.plan
    calls = []

    def flaky(subject):
        calls.append(subject)
        if len(calls) == 1:
            raise ValueError("first")

    @entry
    def scoped():
        with pytest.raises(ValueError):
            once(flaky, plan)
        once(flaky, plan)
        once(flaky, plan)
        a = plan_verification.verify_compiled_sql_plan(plan)
        b = plan_verification.verify_compiled_sql_plan(plan)
        return a, b

    a, b = scoped()
    assert len(calls) == 2  # the failure re-ran; the success was not repeated
    assert a is not b
    assert (a.plan, a.completed, a.selected_owner) == (
        b.plan,
        b.completed,
        b.selected_owner,
    )


def test_marks_key_every_argument_by_identity():
    from pietto._project.project_verification_scope import entry, once

    seen = []

    def check(*subjects):
        seen.append(subjects)

    one, two, three = object(), object(), object()

    @entry
    def scoped():
        once(check, one, two)
        once(check, one, three)
        once(check, one, two)

    scoped()
    assert seen == [(one, two), (one, three)]


def test_marks_keep_their_subjects_alive_until_the_scope_ends():
    """No identity can be reused inside a scope: a marked object stays alive while
    the scope is open, even with every other reference gone, and is released when
    the outermost call returns."""
    import gc
    import weakref

    from pietto._project import project_verification_scope as scope

    class Subject:
        pass

    refs, runs = [], []

    def check(subject):
        runs.append(id(subject))

    @scope.entry
    def scoped():
        for _ in range(3):
            subject = Subject()
            refs.append(weakref.ref(subject))
            scope.once(check, subject)
            del subject
        gc.collect()
        assert all(r() is not None for r in refs)
        fresh = [Subject() for _ in range(64)]
        assert not {id(f) for f in fresh} & set(runs)

    scoped()
    gc.collect()
    assert len(runs) == 3 and all(r() is None for r in refs)


def test_scope_ends_with_the_outermost_call():
    from pietto._project import project_verification_scope as scope

    runs = []

    def check(subject):
        runs.append(subject)

    subject = object()

    @scope.entry
    def passing():
        scope.once(check, subject)

    @scope.entry
    def failing(error):
        scope.once(check, subject)
        raise error

    passing()
    for error in (ValueError("x"), KeyboardInterrupt()):
        with pytest.raises(type(error)):
            failing(error)
        assert getattr(scope._local, "scope", None) is None
    passing()
    assert len(runs) == 4


def test_scope_is_per_thread():
    import contextvars

    from pietto._project.project_verification_scope import entry, once

    runs = []
    subject = object()
    ready, release = threading.Event(), threading.Event()
    copied = []

    def check(value):
        runs.append(threading.get_ident())

    @entry
    def holder():
        once(check, subject)
        copied.append(contextvars.copy_context())
        ready.set()
        release.wait(10)

    @entry
    def other():
        once(check, subject)

    worker = threading.Thread(target=holder)
    worker.start()
    assert ready.wait(10)
    # A context copied from inside the holder's open scope, run on another thread.
    thread = threading.Thread(target=lambda: copied[0].run(other))
    thread.start()
    thread.join(10)
    release.set()
    worker.join(10)
    assert len(runs) == 2 and runs[0] != runs[1]


def test_entries_refuse_generators_and_coroutines():
    from pietto._project.project_verification_scope import boundary, entry

    def generator():
        yield 1

    async def coroutine():
        return 1

    for decorate in (entry, boundary):
        for function in (generator, coroutine):
            with pytest.raises(TypeError, match="VERIFICATION_SCOPE_ENTRY"):
                decorate(function)


def test_owner_boundaries_start_fresh_and_restore_the_outer_scope():
    """Every owner attempt (`open`, each `__next__`) verifies again inside its own
    timing and cancellation boundary; its marks never leak to the caller."""
    from pietto._project import project_verification_scope as scope

    runs = []

    def check(subject):
        runs.append(subject)

    outer, inner = object(), object()

    @scope.boundary
    def attempt(fail=False):
        scope.once(check, outer)
        scope.once(check, inner)
        if fail:
            raise ValueError("attempt")

    @scope.entry
    def caller():
        scope.once(check, outer)
        attempt()
        attempt()
        with pytest.raises(ValueError, match="^attempt$"):
            attempt(fail=True)
        scope.once(check, outer)
        scope.once(check, inner)

    caller()
    assert runs == [outer, *[outer, inner] * 3, inner]
    attempt()
    assert getattr(scope._local, "scope", None) is None


@pytest.fixture(scope="module")
def trees():
    """The parsed `_project` modules, released when this module's tests end."""
    return [
        (path.name, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted((ROOT / "src/pietto/_project").glob("*.py"))
    ]


def test_scope_names_are_used_only_in_plain_form():
    """The inventories below match plain names, so the scope module is used only
    as `from ... import entry, boundary, once`: never import-aliased, imported as
    a module, or called as `entry(f)` instead of decorating."""
    found = 0
    for path in sorted((ROOT / "src/pietto").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if path.name == "project_verification_scope.py" or (
            "project_verification_scope" not in text
        ):
            continue
        tree, imported = ast.parse(text), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(
                    a.name.endswith("project_verification_scope") for a in node.names
                ), path
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").endswith("project_verification_scope"):
                    found += 1
                    assert all(
                        a.asname is None and a.name in ("entry", "boundary", "once")
                        for a in node.names
                    ), path
                    imported |= {a.name for a in node.names}
                else:
                    assert "project_verification_scope" not in {
                        a.name for a in node.names
                    }, path
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in imported & {"entry", "boundary"}, path
    assert found


MEMOIZED = {
    ("model.py", "_verify_compiled_input"),
    ("project_query_block_ir_verification.py", "_verify_compiled_query_block_ir"),
    ("project_sql_plan_verification.py", "_verify_compiled_sql_plan"),
    ("project_compiled_verification.py", "_verify_compiled_emission"),
    ("project_sql_plan_requirements.py", "_verify_compiled_requirement_report"),
    ("project_guard_preparation.py", "_verify_scope"),
    ("project_guard_preparation.py", "_verify_preparation"),
}


def test_memo_inventory_is_exact(trees):
    """Exactly the seven pure structural checks consult the call-scoped marks,
    each at one call site that names its private body."""
    found = []
    for name, tree in trees:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "once"
            ):
                assert node.args and isinstance(node.args[0], ast.Name), name
                found.append((name, node.args[0].id))
    assert sorted(found) == sorted(MEMOIZED)


DECORATED = {
    ("project_compiled_lowering.py", "emit_compiled", "entry"),
    ("project_execution.py", "compiled_output", "entry"),
    ("project_execution.py", "prepare_compiled_execution", "entry"),
    ("project_execution_binding_verification.py", "verify_binding", "entry"),
    ("project_execution_binding_verification.py", "verify_template", "entry"),
    ("project_execution_mysql.py", "MySQLExecution.__next__", "boundary"),
    ("project_execution_mysql.py", "MySQLExecution.open", "boundary"),
    ("project_execution_postgres.py", "PostgresExecution.__next__", "boundary"),
    ("project_execution_postgres.py", "PostgresExecution.open", "boundary"),
    (
        "project_execution_postgres_adbc.py",
        "PostgresADBCExecution.__next__",
        "boundary",
    ),
    ("project_execution_postgres_adbc.py", "PostgresADBCExecution.open", "boundary"),
    ("project_execution_template.py", "bind_values", "entry"),
    ("project_execution_template.py", "compatible_compiled_values", "entry"),
    ("project_execution_template.py", "describe_compiled_binding", "entry"),
    ("project_execution_template.py", "prepare_compiled_template", "entry"),
    ("project_execution_template.py", "prepare_live_template", "entry"),
    ("project_guard_preparation.py", "prepare_compiled_guarded", "entry"),
    ("project_guard_preparation.py", "prepare_guarded_output", "entry"),
    ("project_guard_preparation.py", "prepare_guarded_template", "entry"),
    ("project_guard_program.py", "prepare_program", "entry"),
    ("project_guard_program.py", "statement_for", "entry"),
    ("project_guard_rendering.py", "render_guard", "entry"),
    ("project_guard_verification.py", "verify_native_guard", "entry"),
    ("project_guard_verification.py", "verify_program", "entry"),
    ("project_guard_verification.py", "verify_statement", "entry"),
    ("project_refinement.py", "prepare_compiled_refinement", "entry"),
    ("project_refinement_verification.py", "verify_native", "entry"),
    ("project_refinement_verification.py", "verify_refinement", "entry"),
    ("project_result_output.py", "prepare_output", "entry"),
    ("project_result_output.py", "verify_output", "entry"),
    ("project_sql_emission_inspection.py", "inspect_project_sql_emission", "entry"),
}


def test_scope_entry_inventory_is_exact(trees):
    """Scopes open only at the declared public calls and owner attempts. No entry
    runs caller-supplied code: none lives in the job, Arrow or store layers (their
    providers, sinks, fences and commit re-checks) or takes a callable."""
    found, parameters, decorated = set(), {}, 0
    for module, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                decorated += any(
                    isinstance(d, ast.Name) and d.id in ("entry", "boundary")
                    for d in node.decorator_list
                )
        owners = [tree, *(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef))]
        for owner in owners:
            prefix = owner.name + "." if isinstance(owner, ast.ClassDef) else ""
            for node in owner.body:
                if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                for d in node.decorator_list:
                    if isinstance(d, ast.Name) and d.id in ("entry", "boundary"):
                        found.add((module, prefix + node.name, d.id))
                        parameters[module, prefix + node.name] = {
                            a.arg for a in ast.walk(node.args) if isinstance(a, ast.arg)
                        }
    assert len(found) == decorated
    assert found == DECORATED
    for (module, name), names in parameters.items():
        assert not module.startswith(("project_job", "project_arrow")), name
        assert not names & {"provider", "sink", "callback", "consumer"}, name


def test_every_scope_entry_is_reached_by_a_route(request):
    """Each declared entry runs inside at least one budget route, as the route's
    public call or nested in it, so the budget law covers every scope it opens."""
    import importlib
    import inspect

    codes = {}
    for module, name, kind in DECORATED:
        if kind == "entry" and name not in OWNER_ONLY:
            wrapper = getattr(
                importlib.import_module("pietto._project." + module[:-3]), name
            )
            codes[inspect.unwrap(wrapper).__code__] = name
    assert len(codes) == sum(
        kind == "entry" and name not in OWNER_ONLY for _m, name, kind in DECORATED
    )
    # Every route is built before monitoring starts, so only the public calls count.
    calls = [_route(route, _world(request, route))[0] for route in ROUTES]
    reached = set()
    free = [i for i in range(6) if MON.get_tool(i) is None]
    tool = free[-1]
    MON.use_tool_id(tool, "pietto-entry-coverage")
    try:
        MON.register_callback(
            tool, MON.events.PY_START, lambda code, offset: reached.add(codes[code])
        )
        for code in codes:
            MON.set_local_events(tool, code, MON.events.PY_START)
        for call in calls:
            call()
    finally:
        for code in codes:
            MON.set_local_events(tool, code, 0)
        MON.register_callback(tool, MON.events.PY_START, None)
        MON.free_tool_id(tool)
    assert sorted(set(codes.values()) - reached) == []


def test_marks_never_hold_job_layer_authority(request, monkeypatch):
    """Marks keep their subjects alive until the call ends, so they must never
    hold a job-layer authority object that the runtime tracks by weak reference.
    Every memoized check refuses a foreign object, so no mark can record one."""
    from pietto._project import project_verification_scope as scope

    real, seen = scope.once, []

    def recording(check, *subjects):
        seen.extend(subjects)
        return real(check, *subjects)

    for module in list(sys.modules.values()):
        if (
            getattr(module, "__name__", "").startswith("pietto._project.")
            and getattr(module, "once", None) is real
        ):
            monkeypatch.setattr(module, "once", recording)
    for route in ROUTES:
        _route(route, _world(request, route))[0]()
    monkeypatch.undo()
    assert seen
    for subject in seen:
        assert not type(subject).__module__.startswith("pietto._project.project_job")

    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_guard_preparation import GuardPreparationError

    refusals = {
        "_verify_compiled_input": (AttributeError, "description"),
        "_verify_compiled_query_block_ir": (CompiledError, "^COMPILED_IR_ROOT$"),
        "_verify_compiled_sql_plan": (CompiledError, "^COMPILED_PLAN_ROOT$"),
        "_verify_compiled_emission": (CompiledError, "^COMPILED_EMISSION_ROOT$"),
        "_verify_compiled_requirement_report": (
            ValueError,
            "^COMPILED_REQUIREMENT_PLAN$",
        ),
        "_verify_scope": (GuardPreparationError, "^GUARD_PREPARATION_ROOT$"),
        "_verify_preparation": (GuardPreparationError, "^GUARD_PREPARATION_ROOT$"),
    }
    modules = {
        "model.py": model,
        "project_query_block_ir_verification.py": ir_verification,
        "project_sql_plan_verification.py": plan_verification,
        "project_compiled_verification.py": compiled_verification,
        "project_sql_plan_requirements.py": requirements,
        "project_guard_preparation.py": guard_preparation,
    }

    @scope.entry
    def foreign():
        for module, name in sorted(MEMOIZED):
            check = getattr(modules[module], name)
            arity = check.__code__.co_argcount
            error, message = refusals[name]
            with pytest.raises(error, match=message):
                scope.once(check, *(object() for _ in range(arity)))
        assert scope._local.scope == {}

    foreign()


def test_origin_vocabularies_are_built_once_per_check(ordinary, monkeypatch):
    """L1: the role and provenance vocabularies are iterated once per check,
    not once per origin."""
    from enum import EnumType

    _original, built, _values = ordinary
    root = _load(built)
    origins = [
        r for r in root.records.values() if r.address.kind == "requirement_origin"
    ]
    assert len(origins) >= 2
    iterations: Counter = Counter()
    real = EnumType.__iter__

    def counting(cls):
        iterations[cls] += 1
        return real(cls)

    monkeypatch.setattr(EnumType, "__iter__", counting)
    requirements.verify_compiled_requirement_inputs(root.records)
    monkeypatch.undo()
    assert iterations[requirements.sql.ProjectSQLOriginRole] == 1
    assert iterations[requirements.sql.ProjectSQLOriginProvenance] == 1


def test_requirement_index_check_is_linear(ordinary):
    """L3: each index reads every entry's member keys once, not once per key."""
    import types

    _original, built, values = ordinary
    artifact = emit_compiled(_load(built), values)
    report, verification = artifact.request.report, artifact.request.verification
    body = BODIES["verify_compiled_requirement_report"]
    lambdas = [
        c
        for c in body.__code__.co_consts
        if isinstance(c, types.CodeType) and c.co_name == "<lambda>"
    ]
    assert len(lambdas) == 5
    calls: Counter = Counter()
    free = [i for i in range(6) if MON.get_tool(i) is None]
    tool = free[-1]
    MON.use_tool_id(tool, "pietto-index-linearity")
    try:
        MON.register_callback(
            tool, MON.events.PY_START, lambda code, offset: calls.update([code])
        )
        for code in lambdas:
            MON.set_local_events(tool, code, MON.events.PY_START)
        body(report, verification)
    finally:
        for code in lambdas:
            MON.set_local_events(tool, code, 0)
        MON.register_callback(tool, MON.events.PY_START, None)
        MON.free_tool_id(tool)
    assert len(report.entries) >= 2
    assert sum(calls.values()) == 5 * len(report.entries)


def test_unknown_origin_role_or_provenance_is_refused(ordinary):
    """L1: every origin's role and provenance are still checked, with the code."""
    from pietto._project.project_compiled_schema import FIELDS, CompiledError

    _original, built, _values = ordinary
    records = _load(built).records
    origins = [r for r in records.values() if r.address.kind == "requirement_origin"]
    names = FIELDS["requirement_origin"]
    for origin in (origins[0], origins[-1]):
        for field_name in ("role", "provenance"):
            values = list(origin.values)
            values[names.index(field_name)] = "unknown"
            damaged = dict(records)
            damaged[origin.address] = dataclasses.replace(origin, values=tuple(values))
            with pytest.raises(
                CompiledError, match="^COMPILED_REQUIREMENT_ORIGIN_KIND$"
            ):
                requirements.verify_compiled_requirement_inputs(damaged)


def test_damaged_requirement_indexes_report_the_index_category(ordinary):
    """L3: a missing, extra, duplicated or reordered member, a wrong key order, a
    list bucket or a plain mapping is refused with the index code."""
    from types import MappingProxyType

    _original, built, values = ordinary
    artifact = emit_compiled(_load(built), values)
    report, verification = artifact.request.report, artifact.request.verification
    stranger = object()

    def damages(index):
        items = list(index.items())
        key, bucket = max(items, key=lambda item: len(item[1]))
        changed = {
            "missing": bucket[:-1],
            "extra": (*bucket, stranger),
            "duplicate": (*bucket, bucket[0]),
            "list": list(bucket),
        }
        if len(bucket) >= 2:
            changed["reordered"] = bucket[::-1]
        outsider = [e for e in report.entries if all(e is not b for b in bucket)]
        if outsider:
            changed["foreign"] = (outsider[0], *bucket[1:])
        for kind, value in changed.items():
            yield kind, MappingProxyType({**index, key: value})
        yield "mapping", dict(index)
        if len(items) >= 2:
            yield "key_order", MappingProxyType(dict(items[::-1]))

    def refused():
        requirements.verify_compiled_requirement_report(report, verification)
        kinds = set()
        for name in (
            "by_family",
            "by_subject",
            "by_definition",
            "by_stage",
            "by_input_use",
        ):
            for kind, index in damages(getattr(report, name)):
                kinds.add(kind)
                damaged = dataclasses.replace(report, **{name: index})
                with pytest.raises(ValueError, match="^COMPILED_REQUIREMENT_INDEX$"):
                    requirements.verify_compiled_requirement_report(
                        damaged, verification
                    )
        return kinds

    assert refused() == {
        "missing",
        "extra",
        "duplicate",
        "list",
        "reordered",
        "foreign",
        "mapping",
        "key_order",
    }


def _outcome(function, raw):
    from pietto._project.project_compiled_schema import CompiledError

    try:
        function(raw)
    except CompiledError as error:
        return str(error)
    return None


def test_bounded_fast_path_agrees_with_the_byte_loop(monkeypatch):
    """L2: the accept-only fast path never accepts what the byte loop refuses,
    so every outcome and code still comes from the gate or the loop. Exhaustive
    over a small alphabet at depths 1 and 2, then adversarial at the real depth."""
    import itertools

    from pietto._project import project_compiled_schema as schema

    alphabet = (b'"', b"\\", b"[", b"}", b"\n", b"{")
    corpus = [
        b"".join(p) for n in range(1, 7) for p in itertools.product(alphabet, repeat=n)
    ]
    for depth in (1, 2):
        monkeypatch.setattr(schema, "MAX_DEPTH", depth)
        fast = 0
        for raw in corpus:
            assert _outcome(schema._bounded, raw) == _outcome(
                schema._bounded_scan, raw
            ), (depth, raw)
            fast += schema._shallow(raw)
        assert fast > 1000
    monkeypatch.undo()
    deep = schema.MAX_DEPTH
    adversarial = (
        b"[" * deep + b"]" * deep,
        b"[" * (deep + 1) + b"]" * (deep + 1),
        b"{" * (deep // 2)
        + b"[" * (deep // 2)
        + b"]" * (deep // 2)
        + b"}" * (deep // 2),
        b"]",
        b"[]]",
        b"{]",
        b'"' + b"[" * (deep + 8),
        b'"\\"' + b"[" * (deep + 8),
        b'"\\\\"' + b"[" * (deep + 1),
        b'["\\"[", "]"]',
        b"[" + b"0," * (schema._FAST_BYTES // 2) + b"0]",
    )
    for raw in adversarial:
        assert _outcome(schema._bounded, raw) == _outcome(schema._bounded_scan, raw)


def test_canonical_encodings_never_reach_the_byte_loop(ordinary, monkeypatch):
    """L2: canonical encoder output takes the fast path; only crafted rejects
    reach the byte loop, which still reports their codes."""
    from pietto._project import project_compiled_schema as schema

    _original, built, _values = ordinary
    real, scans = schema._bounded_scan, []

    def scan(raw):
        scans.append(len(raw))
        return real(raw)

    monkeypatch.setattr(schema, "_bounded_scan", scan)
    _load(built).verify()
    schema.content_pin(built.payload)
    assert scans == []
    for raw, code in (
        (b"[" * (schema.MAX_DEPTH + 1), "COMPILED_DEPTH_LIMIT"),
        (b"]", "COMPILED_JSON"),
    ):
        with pytest.raises(schema.CompiledError, match="^%s$" % code):
            schema._bounded(raw)
    assert len(scans) == 2
