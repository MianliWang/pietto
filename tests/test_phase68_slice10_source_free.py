"""Actual compiler build to resolved input; source elaboration is build-only."""

from pathlib import Path

import pytest

from _pietto_phase68_slice4_probe import template
import _pietto_phase67_result_product_probe as original
from pietto._project.project_compiled_build import build_compiled
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_schema import CompiledError
from pietto._project.project_completed_semantics import derive_compiled_semantics


def forbidden(*args, **kwargs):
    raise AssertionError("source-language elaboration reached from compiled input")


def test_actual_build_then_new_roots_and_text_rederivation(tmp_path, monkeypatch):
    source = original.source("postgres").replace("renamed = id", 'renamed = "seed"')
    live = template(tmp_path / "original", source)
    expected_sql = live.artifact.rendered.sql
    built = build_compiled(live.artifact)
    original_path_read = Path.read_bytes

    def no_source_read(path):
        assert path.suffix != ".pietto" and path.name != "pietto.toml"
        return original_path_read(path)

    import pietto.parser_api as parser
    from pietto._project import (
        model,
        project_completed_semantics,
        project_execution_template,
    )

    monkeypatch.setattr(Path, "read_bytes", no_source_read)
    monkeypatch.setattr(parser, "parse_source", forbidden)
    monkeypatch.setattr(model, "build_empty_project_semantic_result", forbidden)
    monkeypatch.setattr(
        project_completed_semantics,
        "build_project_completed_semantic_result",
        forbidden,
    )
    monkeypatch.setattr(project_execution_template, "_syntax_image", forbidden)
    monkeypatch.setattr(project_execution_template, "_specialize", forbidden)
    moved = tmp_path / "unrelated"
    moved.mkdir()
    monkeypatch.chdir(moved)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert loaded is not built.root and loaded.scope is not built.root.scope
    a = derive_compiled_semantics(loaded, ("a",))
    b = derive_compiled_semantics(loaded, ("longer",))
    again = derive_compiled_semantics(loaded, ("a",))
    with pytest.raises(CompiledError, match="BINDING_VALUE"):
        derive_compiled_semantics(loaded, (True,))
    for result, expected in ((a, 1), (b, 6), (again, 1)):
        literals = [
            f
            for f in result.facts
            if f.address.kind == "literal" and f.value in ("a", "longer")
        ]
        assert len(literals) == 1
        assert literals[0].realization.domain["max_characters"] == expected
    assert a.facts is not b.facts and a.facts is not again.facts
    assert a.values == ("a",) and b.values == ("longer",)
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_sql_emission_inspection import (
        inspect_project_sql_emission,
    )

    for supplied in (("a",), ("longer",), ("a",)):
        artifact = emit_compiled(loaded, supplied)
        observed = inspect_project_sql_emission(artifact, artifact.request)
        assert observed.sql == expected_sql
        assert artifact.fixed_values[0].value == supplied[0]
        assert artifact.parameter_uses[0].server_index == 1

    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project.project_result_output import prepare_output

    compiled_template = prepare_template(emit_compiled(loaded, ("seed",)))
    pairs = [[compiled_template.slots[0], "a"]]
    binding_a = bind_values(compiled_template, pairs)
    pairs[0][1] = "changed"
    pairs.clear()
    binding_b = bind_values(
        compiled_template, ((compiled_template.slots[0], "longer"),)
    )
    binding_again = bind_values(compiled_template, ((compiled_template.slots[0], "a"),))
    for binding, length in ((binding_a, 1), (binding_b, 6), (binding_again, 1)):
        output = prepare_output(binding.artifact, binding=binding)
        assert output.columns[0].realization.domain["max_characters"] == length
        assert tuple(c.field.shape.canonical.name for c in output.columns) == (
            "Text",
            "Int",
        )
    assert binding_a.values == ("a",)


def test_fresh_process_without_query_project_or_test_helpers(tmp_path):
    import json
    import shutil
    import subprocess
    import sys

    source_path = tmp_path / "build-only-project"
    live = template(
        source_path,
        original.source("postgres").replace("renamed = id", 'renamed = "seed"'),
    )
    built = build_compiled(live.artifact)
    bundle = tmp_path / "compiled.json"
    bundle.write_bytes(built.payload)
    bundle.chmod(0o600)
    handoff = tmp_path / "trusted-handoff.json"
    handoff.write_text(
        json.dumps(
            {
                "pin": built.pin,
                "producer": built.producer,
                "compatibility": built.compatibility,
            }
        )
    )
    handoff.chmod(0o600)
    shutil.rmtree(source_path)
    unrelated = tmp_path / "runtime-cwd"
    unrelated.mkdir()
    program = r"""
import sys
if sys.stdin.read(1) != "g":
    raise RuntimeError("missing registered launch gate")
import json
from pathlib import Path
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_lowering import emit_compiled
from pietto._project.project_execution_template import prepare_template, bind_values
from pietto._project.project_result_output import prepare_output
import pietto.ast_nodes as nodes
import pietto.parser_api as parser
from pietto._project import model, project_completed_semantics, project_execution_template

def forbidden(*args, **kwargs):
    raise AssertionError("source-language entry used")

parser.parse_source = forbidden
model.build_empty_project_semantic_result = forbidden
project_completed_semantics.build_project_completed_semantic_result = forbidden
project_execution_template._syntax_image = forbidden
project_execution_template._specialize = forbidden
for name in ("Script", "QueryDef", "TableDef", "SourceDef", "LiteralExpr", "NameExpr", "DottedNameExpr", "TypeExpr"):
    getattr(nodes, name).__new__ = forbidden
model.ProjectParseCheckResult.__new__ = forbidden
original_read = Path.read_bytes

def closed_read(path):
    if path.suffix == ".pietto" or path.name == "pietto.toml":
        raise AssertionError("query-source read")
    return original_read(path)

Path.read_bytes = closed_read
handoff = json.loads(Path(sys.argv[2]).read_text())
root = load_compiled(Path(sys.argv[1]).read_bytes(), expected_pin=handoff["pin"], accepted_producer=handoff["producer"], accepted_compatibility=tuple(handoff["compatibility"]))
template = prepare_template(emit_compiled(root, ("seed",)))
for value, size in (("a", 1), ("longer", 6), ("a", 1)):
    bound = bind_values(template, ((template.slots[0], value),))
    output = prepare_output(bound.artifact, binding=bound)
    assert output.columns[0].realization.domain["max_characters"] == size
assert not any(name.startswith(("_pietto_", "test_")) for name in sys.modules)
assert not any(name == "pyarrow" or name.startswith(("adbc_driver", "psycopg", "mysql.connector")) for name in sys.modules)
print(json.dumps({"bindings": 3, "source_ast_constructions": 0, "source_calls": 0, "optional_imports": 0}))
"""
    with subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", program, str(bundle), str(handoff)],
        cwd=unrelated,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as child:
        record = tmp_path / "registered-process.json"
        record.write_text(
            json.dumps(
                {
                    "pid": child.pid,
                    "purpose": "fresh source-free core consumer",
                    "executable": sys.executable,
                }
            )
        )
        try:
            stdout, stderr = child.communicate(input="g", timeout=60)
        except BaseException:
            child.kill()
            child.communicate(timeout=10)
            raise
        assert child.returncode == 0, stderr[-6000:]
        observed = json.loads(stdout)
        assert observed == {
            "bindings": 3,
            "source_ast_constructions": 0,
            "source_calls": 0,
            "optional_imports": 0,
        }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "seed,values,bad",
    [
        ("true", (False, True, False), (0, 1, None)),
        ("1", (-(2**63), 2**63 - 1, -(2**63)), (True, 1.0, None)),
        ("1.5", (-0.0, 1.25, -0.0), (1, True, float("inf"), float("nan"))),
        ('"seed"', ("", "雪é😀  ? %s $1", ""), (b"x", None, "\ud800")),
    ],
)
def test_all_bindable_tags_a_b_a_current_evidence(tmp_path, target, seed, values, bad):
    from dataclasses import replace
    from pietto._project.project_execution_template import (
        prepare_template,
        bind_values,
        BindingError,
    )
    from pietto._project.project_execution_binding_verification import atom
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_sql_plan_requirements import (
        verify_compiled_requirement_report,
    )

    source = template(
        tmp_path / "four-tags",
        original.source(target).replace("renamed = id", "renamed = " + seed),
        target=target,
    )
    expected = tuple(
        bind_values(source, ((source.slots[0], value),)) for value in values
    )
    built = build_compiled(source.artifact)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    loaded = prepare_template(
        emit_compiled(root, tuple(v.value for v in source.artifact.fixed_values))
    )
    observed = []
    for value, reference in zip(values, expected, strict=True):
        pairs = [[loaded.slots[0], value]]
        bound = bind_values(loaded, pairs)
        pairs[0][1] = None
        pairs.clear()
        assert tuple(atom(v) for v in bound.values) == tuple(
            atom(v) for v in reference.values
        )
        assert tuple(atom(v) for v in bound.arguments) == tuple(
            atom(v) for v in reference.arguments
        )
        actual_output = prepare_output(bound.artifact, binding=bound)
        source_output = prepare_output(reference.artifact, binding=reference)
        assert tuple(
            (
                c.realization.tag,
                c.realization.storage,
                c.realization.domain,
                c.realization.nullable,
            )
            for c in actual_output.columns
        ) == tuple(
            (
                c.realization.tag,
                c.realization.storage,
                c.realization.domain,
                c.realization.nullable,
            )
            for c in source_output.columns
        )
        observed.append(bound)
    for value in bad:
        with pytest.raises(BindingError):
            bind_values(loaded, ((loaded.slots[0], value),))
    from pietto._project.project_execution_template import (
        describe_compiled_binding,
        compatible_compiled_values,
    )

    route = "postgres_rows" if target == "postgres" else "mysql_rows"
    descriptions = tuple(
        describe_compiled_binding(value, route=route) for value in observed
    )
    assert len({d.binding_reference for d in descriptions}) == 3
    assert compatible_compiled_values(observed[0], observed[2], route=route)
    assert not compatible_compiled_values(observed[0], observed[1], route=route)
    assert descriptions[0].content_pin == descriptions[2].content_pin == built.pin
    assert descriptions[0].query == descriptions[2].query
    assert descriptions[0].target[2] == route
    old = observed[0].artifact.request.report
    current = observed[1].artifact.request
    with pytest.raises(ValueError):
        verify_compiled_requirement_report(
            replace(old, verification=current.verification, plan=current.plan),
            current.verification,
        )


def test_complete_named_corpus_in_fresh_source_free_process(tmp_path):
    """A fresh portability witness reuses the original cases and their oracles."""
    from dataclasses import asdict
    import json
    import shutil
    import subprocess
    import sys
    from _pietto_phase68_slice6_cases import CASES, original as source_artifact
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from test_phase68_slice6_refinement import capabilities
    from test_phase68_slice4_binding import _proof_artifact
    from pietto._project.project_guard_preparation import prepare_guarded_output
    from pietto._project.project_refinement import prepare_refinement, TieRefinement
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    source_root = tmp_path / "build-only"
    bundles = tmp_path / "bundles"
    bundles.mkdir()
    declarations = []

    def retain(artifact, name, guarded=None, refined=False):
        output = (
            prepare_output(artifact)
            if guarded is None
            else prepare_guarded_output(guarded)
        )
        refinement = (
            prepare_refinement(
                artifact, capabilities(artifact), policy=TieRefinement(), output=output
            )
            if refined
            else None
        )
        built = build_compiled(artifact, guarded=guarded, refinement=refinement)
        path = bundles / (str(len(declarations)) + ".json")
        path.write_bytes(built.payload)
        declarations.append(
            dict(
                name=name,
                path=str(path),
                pin=built.pin,
                producer=built.producer,
                compatibility=built.compatibility,
                values=[
                    scalar_wire(Scalar(value.tag.value, value.value))
                    for value in artifact.fixed_values
                ],
                sql=artifact.rendered.sql.decode(),
                guarded=guarded is not None,
                refined=refinement is not None,
                coordinates=None
                if refinement is None
                else [[asdict(c) for c in u.coordinates] for u in refinement.units],
                requests=len(
                    artifact.request.verification.completed.single_match_requests
                ),
                selected_requests=len(artifact.request.plan.single_matches),
            )
        )

    cell = 0
    excluded = []
    for target in ("postgres", "mysql"):
        for case, variant in (*CASES, ("R2_bound", "range")):
            artifact = source_artifact(source_root / str(cell), target, case, variant)
            cell += 1
            if artifact is None:
                assert target == "mysql" and (case, variant) in (
                    ("V_join_full", "null_keys"),
                    ("A_window_groups", "exclude"),
                )
                excluded.append((target, case, variant))
                continue
            retain(artifact, [target, case, variant, "ordinary"])
            retain(artifact, [target, case, variant, "refined"], refined=True)
        for case in manifest():
            if target == "mysql" and case["options"].get("postgres_only", False):
                continue
            preparation = case_preparation(source_root / str(cell), target, case)
            cell += 1
            retain(
                preparation.artifact,
                [target, case["name"], "guarded"],
                guarded=preparation,
                refined=case["options"].get("refined", False),
            )
    retained = _proof_artifact(source_root / str(cell), retained=True).artifact
    assert retained is not None
    retain(retained, ["postgres", "retained_unselected"])
    from test_phase68_slice10_compiled_families import retained_unmapped_source

    with pytest.MonkeyPatch.context() as patcher:
        unmapped = retained_unmapped_source(
            source_root / "unmapped", "postgres", "key", patcher
        ).artifact
    assert unmapped is not None
    retain(unmapped, ["postgres", "retained_unselected_unmapped_key"])
    assert len(excluded) == 2
    handoff = tmp_path / "trusted-handoff.json"
    handoff.write_text(json.dumps(declarations, ensure_ascii=False))
    shutil.rmtree(source_root)
    cwd = tmp_path / "runtime"
    cwd.mkdir()
    program = r"""
import sys
if sys.stdin.read(1) != "g":
    raise RuntimeError("missing registered launch gate")
import importlib
import json
from dataclasses import asdict
from pathlib import Path
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_lowering import emit_compiled
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_execution_template import prepare_template, bind_values
from pietto._project.project_result_output import prepare_output
from pietto._project.project_guard_preparation import prepare_compiled_guarded, prepare_guarded_template
from pietto._project.project_guard_program import prepare_program, statement_for, pure_static_proofs
from pietto._project.project_guard_rendering import render_guard
from pietto._project.project_guard_verification import verify_native_guard
from pietto._project.project_refinement import prepare_compiled_refinement
from pietto._project.project_refinement_rendering import render
from pietto._project.project_refinement_verification import verify_native
import pietto.ast_nodes as nodes
from pietto._project import model, trusted_source

def forbidden(*args, **kwargs):
    raise AssertionError("source-language boundary invoked")

blocked = []
for module_name, names in (
    ("pietto.parser_api", ("parse_source",)),
    ("pietto._project.model", ("build_empty_project_semantic_result",)),
    ("pietto._project.project_completed_semantics", ("build_project_completed_semantic_result",)),
    ("pietto._project.project_execution_template", ("_syntax_image", "_specialize")),
    ("pietto._project.discovery", ("discover_project_inputs",)),
    ("pietto._project.config", ("load_project_config", "_read_project_config_bytes")),
    ("pietto._project.trusted_source", ("_load_trusted_source",)),
    ("pietto._project.package_loader", ("_load_root_package", "_load_package_content", "_read_trusted_package_file_at")),
    ("pietto._project.module_catalog", ("_build_project_module_catalog_set",)),
    ("pietto._project.module_attribution", ("_build_project_module_attribution_fact_set", "_derive_project_module_attribution_fact_collections")),
):
    module = importlib.import_module(module_name)
    for name in names:
        blocked.append(getattr(module, name))
for module in tuple(sys.modules.values()):
    if module is None or not getattr(module, "__name__", "").startswith("pietto"):
        continue
    for name, value in tuple(vars(module).items()):
        if any(value is function for function in blocked):
            setattr(module, name, forbidden)
for value in tuple(vars(nodes).values()):
    if type(value) is type and (issubclass(value, nodes.Node) or value is nodes.Span):
        value.__new__ = forbidden
model.ProjectParseCheckResult.__new__ = forbidden
trusted_source.ProjectTrustedSourceSnapshot.__new__ = forbidden
assert not Path(sys.argv[2]).exists()
records = json.loads(Path(sys.argv[1]).read_text())
for item in records:
    root = load_compiled(Path(item["path"]).read_bytes(), expected_pin=item["pin"],
        accepted_producer=item["producer"], accepted_compatibility=tuple(item["compatibility"]))
    values = tuple(scalar_read(value).value for value in item["values"])
    artifact = emit_compiled(root, values)
    assert artifact.rendered.sql.decode() == item["sql"], item["name"]
    preparation = prepare_compiled_guarded(artifact) if item["guarded"] else None
    template = prepare_template(artifact) if preparation is None else prepare_guarded_template(preparation)
    bound = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    assert len(bound.artifact.request.plan.all_single_matches) == item["requests"], item["name"]
    assert len(bound.artifact.request.plan.single_matches) == item["selected_requests"], item["name"]
    if item["refined"]:
        refinement = prepare_compiled_refinement(bound.artifact, binding=bound, guarded=bound.guarded)
        coordinates = [[asdict(c) for c in u.coordinates] for u in refinement.units]
        assert json.loads(json.dumps(coordinates)) == item["coordinates"], item["name"]
        assert verify_native(render(refinement.statement, bound.artifact), refinement) == ()
    else:
        refinement = None
    if bound.guarded is not None:
        guards = prepare_program(bound.guarded, binding=bound, refinement=refinement)
        if any(not pure_static_proofs(guards, subject) for subject in guards.subjects):
            verify_native_guard(render_guard(statement_for(guards, "guard")))
    elif refinement is None:
        prepare_output(bound.artifact, binding=bound)
assert not any(name.startswith(("_pietto_", "test_")) for name in sys.modules)
assert not any(name == "pyarrow" or name.startswith(("adbc_driver", "psycopg", "mysql.connector")) for name in sys.modules)
print(json.dumps({"cases":len(records),"source_calls":0,"source_ast_constructions":0}))
"""
    with subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", program, str(handoff), str(source_root)],
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as child:
        (tmp_path / "registered-corpus-process.json").write_text(
            json.dumps(
                dict(
                    pid=child.pid,
                    purpose="complete named source-free core corpus",
                    executable=sys.executable,
                    cases=len(declarations),
                )
            )
        )
        try:
            # A hang guard, not a speed claim: the child verifies every bundle
            # while all four xdist workers may still be busy on a 4-vCPU runner.
            stdout, stderr = child.communicate(input="g", timeout=1800)
        except BaseException:
            child.kill()
            child.communicate(timeout=10)
            raise
        assert child.returncode == 0, stderr[-6000:]
        assert json.loads(stdout) == dict(
            cases=len(declarations), source_calls=0, source_ast_constructions=0
        )
