"""Phase65 portable input, correspondence and actual process-family contracts."""

from __future__ import annotations

import json
from dataclasses import replace
from copy import copy
import base64
from pathlib import Path
import subprocess
import sys

import pytest

from pietto._project import project_sql_plan_portable_schema as schema
from pietto._project import project_sql_plan_pure_boundary as pure
from pietto._project import project_sql_plan_portable as portable
from _pietto_phase65_sql_plan_differential_probe import (
    construction,
    CORPUS,
    assessment,
    observation,
    render,
)

SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


@pytest.mark.parametrize(
    "case",
    (
        "minimal",
        "row",
        "literal_tags",
        "join",
        "path",
        "partial_path",
        "aggregate",
        "hidden_group",
        "hidden_window",
        "window_arguments",
        "hidden_order",
        "set_membership",
    ),
)
def test_current_runtime_families_both_policies(tmp_path, case):
    from test_phase65_slice11_complete_demand_obligation_report import (
        _cases,
        _reported,
        _roots,
        P,
    )

    source, requests = _cases()[case]
    roots = _roots(tmp_path, source, requests)
    for policy in P:
        _, plan, verified, _, report, _ = _reported(roots, policy)
        product = portable.build_project_sql_plan_portable(verified, report=report)
        assert portable.verify_project_sql_plan_portable(product, verified).verified
        decoded = pure.parse_project_sql_plan_document(product.canonical_bytes)
        assert decoded.status is pure.Status.OK and decoded.document == product.document
        inventory = {ref: original for ref, original in product.bindings}
        for demand in plan.demands:
            assert sum(original is demand for original in inventory.values()) == 1


@pytest.mark.parametrize("index", range(11))
def test_all_window_policy_variants_are_finite_typed_evidence(tmp_path, index):
    from test_phase65_slice7_windows_named_window_qualify_staging import (
        FAMILIES,
        _family_source,
        _planned,
    )

    call, frame = FAMILIES[index]
    _, _, verified, _ = _planned(
        tmp_path, _family_source(call, frame, True, "query", "postgres")
    )
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    assert (
        pure.parse_project_sql_plan_document(product.canonical_bytes).status
        is pure.Status.OK
    )


@pytest.mark.parametrize(
    "kind", ("inner", "left", "cross", "right", "full", "semi", "anti")
)
def test_seven_join_kinds_preserve_pre_match_and_output_roles(tmp_path, kind):
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _source,
        _product,
    )

    _, plan, runtime = _product(
        tmp_path, _source(kind, "true", tail="    select:\n        id = lhs.id\n")
    )
    verified = runtime.verification
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    view = pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    )
    join = view.for_kind("project_sql_join")[0]
    wrong = _change(
        product.document, join, "inputs", schema.Value(schema.Tag.SEQUENCE, ())
    )
    assert pure.evaluate_project_sql_plan_document(wrong).status is not pure.Status.OK
    assert len(view.for_kind("project_sql_join_port")) == len(plan.join_ports)


@pytest.mark.parametrize(
    "case",
    (
        "joined_let_where_window",
        "joined_hidden_constant",
        "named_windowed_consumer",
        "named_global_then_window",
    ),
)
def test_window_contexts_keep_selected_hidden_and_named_producers(tmp_path, case):
    from test_phase65_slice7_windows_named_window_qualify_staging import (
        COMPOSED_SOURCES,
        _planned,
    )

    _, _, verified, _ = _planned(tmp_path, COMPOSED_SOURCES[case])
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    assert (
        pure.parse_project_sql_plan_document(product.canonical_bytes).status
        is pure.Status.OK
    )


@pytest.mark.parametrize(
    "case", ("right_limit", "right_global", "shared", "alias", "imports")
)
def test_proof_premises_and_shared_imported_nominal_identity(tmp_path, case):
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _roots,
        _requests,
    )
    from test_phase65_slice11_complete_demand_obligation_report import _reported, P
    from test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries import (
        _source,
    )

    requests = None
    if case == "right_limit":
        from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
            _limited_source,
        )

        source, requests = _limited_source(right_limit=1), _requests
    elif case == "right_global":
        from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
            _tail_source,
        )

        source = (
            _tail_source("global")[0]
            + "query result:\n    from lhs\n    semi join upstream as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n"
        )

        def final_request(completed):
            return (_requests(completed)[-1],)

        requests = final_request
    elif case == "shared":
        from test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols import (
            _repeated_sets,
        )

        source = _repeated_sets(12)
    elif case == "alias":
        source = (
            "type Base = Decimal(10, 2)\ntype Alias = Base\n"
            + _source(type_name="Alias").replace("query result:", "table typed:")
            + "query result:\n    from typed\n    select distinct:\n        value\n"
        )
    else:
        producer = _source(
            "    select distinct:\n        value\n    order by:\n        value\n    limit 1\n",
            kind="table",
        ).replace("table result:", "table capped:")
        (tmp_path / "producer.pietto").write_text(
            producer + "export:\n    table capped\n"
        )
        (tmp_path / "facade.pietto").write_text(
            'import "producer.pietto":\n    table capped as public\nexport:\n    table public\n'
        )
        source = 'import "facade.pietto":\n    table public as chosen\nquery result:\n    from chosen\n    cross join chosen as again:\n        from chosen\n    select distinct:\n        first = chosen.value\n        second = again.value\n    order by:\n        chosen.value\n    limit 0\n'
    _, plan, verified, _, _, _ = _reported(
        _roots(tmp_path, source, requests), P.BIND_SAFE_LITERALS
    )
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    view = pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    )
    if case.startswith("right_"):
        proof = view.for_kind("project_ir_single_match_proof_image")[0]
        assert next(f.value.data for f in proof.fields if f.name == "premise_nodes")
        assert plan.single_match_proofs
        missing = _change(
            product.document,
            proof,
            "premise_nodes",
            schema.Value(schema.Tag.SEQUENCE, ()),
        )
        assert (
            pure.evaluate_project_sql_plan_document(missing).status
            is not pure.Status.OK
        )
    if case == "shared":
        assert len(view.for_kind("project_sql_definition")) == 15
        assert len(view.for_kind("project_sql_input_use")) == 26
    if case == "imports":
        assert view.for_kind("project_module_access_hop")
        item = view.for_kind("project_sql_order_item")[0]
        determination = next(f.value for f in item.fields if f.name == "determination")
        assert isinstance(determination.data, tuple)
        # Missing visible evidence cannot be excused by a nonempty target tuple.
        broken = replace(
            determination,
            data=(
                determination.data[0],
                schema.Value(schema.Tag.SEQUENCE, ()),
                determination.data[2],
            ),
        )
        assert (
            pure.evaluate_project_sql_plan_document(
                _change(product.document, item, "determination", broken)
            ).status
            is not pure.Status.OK
        )


def test_supplied_catalog_remains_an_unmapped_residual(tmp_path):
    import test_phase57_slice8_extension_signature_provider_checking_integration as ext
    from test_phase65_slice13_explicit_target_profile_requirement_assessment import (
        _database,
        _profile,
        REAL_FACTS,
    )
    from pietto.semantic.extension_catalog import (
        ExtensionCatalogLookupScope,
        ExtensionCatalogEntryFamily,
        PostgreSQLCallableIdentity,
    )
    from pietto._project import project_sql_plan_target_assessment as target

    requested = ext._target(
        database_release="18", extension_release="extension-release-9"
    )
    selection = ext._selection(ext._catalog(target=requested))
    scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity("missing", (ext.slice5._builtin(),)),
    )
    catalog = ext._context(
        ext._requirements(ext._key("missing")), (0, scope, selection)
    )
    request = target.prepare_project_sql_target_request(
        _database(), base=_profile(_database(), REAL_FACTS), catalog_context=catalog
    )
    verified = construction(tmp_path / "source", CORPUS[0][1], CORPUS[0][2])
    value = target.build_project_sql_target_assessment(verified, request)
    supplied = target.verify_project_sql_target_assessment(value, verified, request)
    product = portable.build_project_sql_plan_portable(verified, assessment=supplied)
    view = pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    )
    assert view.for_kind("target_catalog_residual")
    record = view.for_kind("project_sql_target_request")[0]
    missing = _change(
        product.document,
        record,
        "catalog_residuals",
        schema.Value(schema.Tag.SEQUENCE, ()),
    )
    assert pure.evaluate_project_sql_plan_document(missing).status is not pure.Status.OK


def test_refinement_keeps_its_complete_original_proof(tmp_path):
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _unique_source,
        _requests,
        _product,
    )

    _, _, runtime = _product(
        tmp_path,
        _unique_source("left", "r.key > 0", via="        via link: l -> r\n"),
        _requests,
    )
    product = runtime.portable()
    assert portable.verify_project_sql_plan_portable(
        product, runtime.verification
    ).verified
    assert pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    ).for_kind("project_refined_match_bounds")


def test_field_roles_cycles_numeric_tags_and_foreign_bindings_reject(tmp_path):
    verified = construction(tmp_path / "source", CORPUS[1][1], CORPUS[1][2])
    product = portable.build_project_sql_plan_portable(verified)
    view = pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    )
    input_use = view.for_kind("project_sql_input_use")[0]
    consumer = next(f.value for f in input_use.fields if f.name == "consumer")
    generated = next(
        r
        for r in view.for_kind("project_sql_source_map_entry")
        if next(f.value.data for f in r.fields if f.name == "nature")
        == "generated_structure"
    )
    fixed = next(
        r
        for r in view.for_kind("project_sql_fixed_literal_value")
        if next(f.value.data for f in r.fields if f.name == "tag") == "Int"
    )
    plan = view.for_kind("project_sql_plan")[0]
    for record, field, replacement in (
        (input_use, "producer", consumer),
        (generated, "nature", schema.Value(schema.Tag.ENUM, "syntax_correspondence")),
        (fixed, "value", schema.Value(schema.Tag.BOOLEAN, True)),
        (plan, "demands", schema.Value(schema.Tag.SEQUENCE, ())),
    ):
        outcome = pure.evaluate_project_sql_plan_document(
            _change(product.document, record, field, replacement)
        )
        assert outcome.status is not pure.Status.OK and outcome.canonical_bytes is None
    records = product.document.records
    for mutation in (
        records[1:],
        (*records, records[-1]),
        (records[0], records[2], records[1], *records[3:]),
    ):
        assert (
            pure.evaluate_project_sql_plan_document(
                replace(product.document, records=mutation)
            ).status
            is not pure.Status.OK
        )
    graft = copy(product)
    object.__setattr__(graft, "bindings", tuple(reversed(product.bindings)))
    assert not portable.verify_project_sql_plan_portable(graft, verified).verified
    foreign = construction(tmp_path / "foreign", CORPUS[1][1], CORPUS[1][2])
    assert not portable.verify_project_sql_plan_portable(product, foreign).verified


def test_raw_refs_and_typed_document_resources_are_bounded(tmp_path):
    verified = construction(tmp_path / "source", CORPUS[0][1], CORPUS[0][2])
    product = portable.build_project_sql_plan_portable(verified)
    data = json.loads(product.canonical_bytes)
    data["records"][0]["ref"][1] = True
    assert pure.decode_project_sql_plan_mapping(data).status is pure.Status.INVALID_REF
    raw = product.canonical_bytes.replace(
        b'"ref":["observation",0]', b'"ref":["observation",-0]', 1
    )
    assert raw != product.canonical_bytes
    assert pure.parse_project_sql_plan_document(raw).status is pure.Status.INVALID_VALUE
    oversized = replace(
        product.document,
        records=(product.document.records[0],) * (schema.MAX_RECORDS + 1),
    )
    assert (
        pure.evaluate_project_sql_plan_document(oversized).status
        is pure.Status.RESOURCE_LIMIT
    )
    with pytest.raises(ValueError, match="checked document"):
        pure.Inspection(pure.Outcome(pure.Status.INVALID_DOCUMENT))


def _available_request_manifest(interpreters):
    from test_validation_performance_interlude_ii_slice2_differential_probe_process_acquisition_optimization import (
        expected_request_manifest,
    )

    current = (sys.version_info.major, sys.version_info.minor)
    assert current in interpreters
    assert set(interpreters) <= set(SUPPORTED_INTERPRETERS)
    return tuple(row for row in expected_request_manifest() if row[2] in interpreters)


def test_process_request_manifest_covers_single_and_both_interpreters():
    import _pietto_differential_process_acquisition as process

    current = (sys.version_info.major, sys.version_info.minor)
    for interpreters in (
        {current: sys.executable},
        {(3, 13): "manifest-only-3.13", (3, 12): "manifest-only-3.12"},
    ):
        expected = _available_request_manifest(interpreters)
        actual = tuple(
            (r.family, r.key, r.cell.version, r.cell.seed, r.cell.mode, r.ambient)
            for r in process.all_requests(interpreters)
        )
        assert actual == expected
        assert {row[2] for row in expected} == set(interpreters)
        assert {row[0] for row in expected} == set(process.FAMILY_ORDER)


def test_registered_process_matrix_and_same_child_origins(
    tmp_path_factory, record_property
):
    import _pietto_differential_process_acquisition as process
    import _pietto_differential_probe_batch as batch

    store = process.acquisition(tmp_path_factory)
    assert process.SUPPORTED_INTERPRETERS == SUPPORTED_INTERPRETERS
    expected = _available_request_manifest(store.interpreters)
    families = tuple(dict.fromkeys(row[0] for row in expected))
    assert families == process.FAMILY_ORDER
    for family in families:
        documents = store.documents(family)
        assert set(documents) == {row[1] for row in expected if row[0] == family}
        if family == "phase65":
            assert len(set(documents.values())) == 1
            for request in process.family_requests(family, store.interpreters):
                origins = store.module_import_origins(request.cell)
                assert tuple(origins) == batch.PHASE65_MODULES
                _, source_root = store._cell_child(request.cell)
                for name, origin in origins.items():
                    expected_file = (
                        source_root / "src" / Path(*name.split(".")).with_suffix(".py")
                    )
                    assert origin == expected_file.resolve()
                    if request.cell.mode != "checkout":
                        assert not origin.is_relative_to(process.REPO_ROOT)
    assert sum(len(requests) for requests in store.plan.values()) == len(expected)
    assert len(store.plan) == len({row[2:5] for row in expected})
    record_property("request_manifest", json.dumps(expected))
    record_property(
        "cell_manifest",
        json.dumps(
            [
                (c.version, c.seed, c.mode, [r.request_id for r in rs])
                for c, rs in store.plan.items()
            ]
        ),
    )


@pytest.mark.parametrize("mode", ("checkout", "relocated", "installed"))
def test_standalone_forward_reverse_batch_and_atomic_failure(
    tmp_path, tmp_path_factory, mode
):
    import _pietto_differential_process_acquisition as process
    import _pietto_differential_probe_batch as batch

    store = process.acquisition(tmp_path_factory)
    version = (sys.version_info.major, sys.version_info.minor)
    child, source_root = store._cell_child(process.Cell(version, "7", mode))
    families = ("phase58", "phase64", "phase65")
    standalone = {}
    for family in families:
        script = child.parent / (batch.FAMILY_MODULES[family] + ".py")
        result = subprocess.run(
            (
                sys.executable,
                str(script),
                "--workspace",
                str(tmp_path / "standalone" / family),
            ),
            cwd=tmp_path,
            env=store.environment(source_root, "7", family + "-parity"),
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        assert (
            result.stderr == b""
            and result.stdout.endswith(b"\n")
            and not result.stdout.endswith(b"\n\n")
        )
        standalone[family] = result.stdout

    for label, order in (
        ("forward", families),
        ("reverse", tuple(reversed(families))),
        ("broken", families),
    ):
        root = tmp_path / label
        root.mkdir()
        requests = [
            {
                "family": family,
                "key": family,
                "ambient": family + "-parity",
                "workspace": str(root / family / "workspace"),
                "cwd": str(root / family / "run"),
            }
            for family in order
        ]
        if label == "broken":
            (root / "phase65" / "workspace" / "minimal" / "0").mkdir(parents=True)
        manifest, output = root / "manifest.json", root / "cell.json"
        manifest.write_text(json.dumps({"requests": requests}))
        result = subprocess.run(
            (
                sys.executable,
                str(child),
                "--manifest",
                str(manifest),
                "--output",
                str(output),
            ),
            cwd=root,
            env=store.environment(source_root, "7", "parity"),
            capture_output=True,
        )
        assert result.stdout == b""
        if label == "broken":
            assert (
                result.returncode != 0
                and not output.exists()
                and not tuple(root.glob("*.pending"))
            )
        else:
            assert result.returncode == 0 and result.stderr == b"", (
                result.stderr.decode("utf-8", "replace")
            )
            payload = json.loads(output.read_bytes())
            assert payload["hash_seed"] == "7" and payload["python_version"] == list(
                version
            )
            assert {
                key: base64.b64decode(value)
                for key, value in payload["results"].items()
            } == standalone
            assert set(payload["module_import_origins"]) == set(batch.PHASE65_MODULES)
            for name, origin in payload["module_import_origins"].items():
                assert (
                    Path(origin)
                    == (
                        source_root / "src" / Path(*name.split(".")).with_suffix(".py")
                    ).resolve()
                )
    failed = tmp_path / "failed-main"
    (failed / "minimal" / "0").mkdir(parents=True)
    script = child.parent / (batch.FAMILY_MODULES["phase65"] + ".py")
    result = subprocess.run(
        (sys.executable, str(script), "--workspace", str(failed)),
        cwd=tmp_path,
        env=store.environment(source_root, "7", "failure"),
        capture_output=True,
    )
    assert result.returncode == 1 and result.stdout == b""
    assert result.stderr == b"Phase65 portable probe failed.\n"


@pytest.mark.parametrize(
    "mode", ("none", "positive", "negative", "conflict", "mismatch", "blocked")
)
def test_explicit_raw_target_evidence_and_applicability(tmp_path, mode, monkeypatch):
    from test_phase65_slice13_explicit_target_profile_requirement_assessment import (
        _database,
        _profile,
        REAL_FACTS,
    )
    from pietto._project import project_sql_plan_target_assessment as target
    from pietto.semantic import capability_providers
    from pietto.semantic.capability_facts import CapabilitySupport

    verified = construction(tmp_path / "source", CORPUS[0][1], CORPUS[0][2])
    database = _database()
    negative = replace(REAL_FACTS[0], support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    facts = (
        (negative,)
        if mode == "negative"
        else (*REAL_FACTS, negative)
        if mode == "conflict"
        else REAL_FACTS
    )
    base = _profile(_database(release="17") if mode == "mismatch" else database, facts)
    overlays = (
        (_profile(_database("mysql", "8.4"), name="wrong", base=base),)
        if mode == "blocked"
        else ()
    )
    request = (
        target.prepare_project_sql_target_request()
        if mode == "none"
        else target.prepare_project_sql_target_request(
            database, base=base, overlays=overlays
        )
    )
    value = target.build_project_sql_target_assessment(verified, request)
    supplied = target.verify_project_sql_target_assessment(value, verified, request)
    monkeypatch.setattr(
        capability_providers,
        "canonical_capability_provider_inputs",
        lambda *_: pytest.fail("Portable path reacquired a provider"),
    )
    product = portable.build_project_sql_plan_portable(verified, assessment=supplied)
    assert portable.verify_project_sql_plan_portable(
        product, verified, assessment=supplied
    ).verified
    view = pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    )
    summary = view.for_kind("project_sql_target_summary")[0]
    false_support = _change(
        product.document,
        summary,
        "posture",
        schema.Value(schema.Tag.ENUM, "complete_requirements_satisfied"),
    )
    assert (
        pure.evaluate_project_sql_plan_document(false_support).status
        is not pure.Status.OK
    )


def test_runtime_accessors_and_original_products_survive_disabled_encoding(
    tmp_path, monkeypatch
):
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
    from pietto._project import project_sql_plan_target_assessment as target

    verified = construction(tmp_path / "source", CORPUS[0][1], CORPUS[0][2])
    view = inspect_project_sql_plan(verified)
    requirements, source_map = view.requirements(), view.source_map()
    supplied = assessment(verified)
    assessed = target.inspect_project_sql_target_assessment(supplied)
    for product in (
        view.portable(),
        requirements.portable(),
        source_map.portable(),
        assessed.portable(),
    ):
        assert (
            pure.parse_project_sql_plan_document(product.canonical_bytes).status
            is pure.Status.OK
        )
    combined = portable.build_project_sql_plan_portable(
        verified,
        report=requirements.verification,
        source_map=source_map.verification,
        assessment=supplied,
    )
    assert portable.verify_project_sql_plan_portable(
        combined, verified, assessment=supplied
    ).verified
    monkeypatch.setattr(
        portable,
        "_encode_context",
        lambda *_: pytest.fail("Old product called encoder"),
    )
    assert view.requirements().entries and view.source_map().source_map.entries
    assert (
        requirements.entries
        and source_map.source_map.links
        and assessed.assessment.demands
    )
    assert portable.verify_project_sql_plan_portable(
        combined, verified, assessment=supplied
    ).verified
    stale = copy(verified)
    object.__setattr__(stale, "envelope", copy(verified.envelope))
    with pytest.raises(portable.TransportError):
        portable.build_project_sql_plan_portable(stale)


def _change(document, record, name, value):
    changed = replace(
        record,
        fields=tuple(
            replace(f, value=value) if f.name == name else f for f in record.fields
        ),
    )
    return replace(
        document,
        records=tuple(changed if r.ref == record.ref else r for r in document.records),
    )


def test_minimal_normal_source_vertical_and_mandatory_terminal(tmp_path, monkeypatch):
    verified = construction(tmp_path / "source", CORPUS[0][1], CORPUS[0][2])
    product = portable.build_project_sql_plan_portable(verified)
    decoded = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert decoded.status is pure.Status.OK
    assert decoded.document == product.document
    assert decoded.canonical_bytes == product.canonical_bytes
    view = pure.Inspection(decoded)
    plan = view.for_kind("project_sql_plan")[0]
    fields = {f.name: f.value for f in plan.fields}
    assert fields["literal_policy"] == schema.Value(
        schema.Tag.ENUM, "preserve_literals"
    )
    exports = fields["exports"].data
    assert type(exports) is tuple and len(exports) == 1
    export_ref = exports[0].data
    assert type(export_ref) is schema.Ref
    export = view.record(export_ref)
    assert export.kind == "project_sql_port"
    assert view.for_kind("project_sql_result_export")
    broken = _change(
        product.document, plan, "result_exports", schema.Value(schema.Tag.SEQUENCE, ())
    )
    rejection = pure.evaluate_project_sql_plan_document(broken)
    assert rejection.status is pure.Status.INVALID_RELATION
    assert rejection.canonical_bytes is None
    monkeypatch.setattr(
        portable, "_encode_context", lambda *_: pytest.fail("Verifier called encoder")
    )
    assert portable.verify_project_sql_plan_portable(product, verified).verified


def test_coherent_document_is_not_runtime_authentication(tmp_path):
    verified = construction(tmp_path / "source", CORPUS[0][1], CORPUS[0][2])
    product = portable.build_project_sql_plan_portable(verified)
    symbol = next(r for r in product.document.records if r.kind == "project_sql_symbol")
    different = _change(
        product.document,
        symbol,
        "label",
        schema.Value(schema.Tag.TEXT, "different_authored_label"),
    )
    outcome = pure.evaluate_project_sql_plan_document(different)
    assert outcome.status is pure.Status.OK
    graft = copy(product)
    object.__setattr__(graft, "document", different)
    object.__setattr__(graft, "canonical_bytes", outcome.canonical_bytes)
    assert portable.verify_project_sql_plan_portable(graft, verified).issues == (
        portable.RuntimeIssue.CORRESPONDENCE,
    )


def test_bound_literals_preserve_typed_values_and_complete_uses(tmp_path):
    verified = construction(tmp_path / "source", CORPUS[1][1], CORPUS[1][2])
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    view = pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    )
    values = [
        next(f.value for f in r.fields if f.name == "value")
        for r in view.for_kind("project_sql_fixed_literal_value")
    ]
    assert schema.Value(schema.Tag.BOOLEAN, True) in values
    assert schema.Value(schema.Tag.FLOAT, (1.25).hex()) in values
    assert schema.Value(schema.Tag.FLOAT, (0.0).hex()) in values
    assert (
        schema.Value(schema.Tag.TEXT, "https://example.invalid/0x/source/😀") in values
    )
    assert any(
        v.tag is schema.Tag.INTEGER and type(v.data) is str and len(v.data) > 50
        for v in values
    )
    assert view.for_kind("project_sql_unary")
    plan = view.for_kind("project_sql_plan")[0]
    for field in ("literal_slots", "bind_uses"):
        outcome = pure.evaluate_project_sql_plan_document(
            _change(
                product.document, plan, field, schema.Value(schema.Tag.SEQUENCE, ())
            )
        )
        assert outcome.status is not pure.Status.OK and outcome.canonical_bytes is None
    envelope = view.for_kind("project_sql_fixed_envelope")[0]
    assert (
        pure.evaluate_project_sql_plan_document(
            _change(
                product.document,
                envelope,
                "values",
                schema.Value(schema.Tag.SEQUENCE, ()),
            )
        ).status
        is not pure.Status.OK
    )


@pytest.mark.parametrize("case", (2, 4))
def test_set_decimal_and_both_order_proofs(tmp_path, case):
    verified = construction(tmp_path / "source", CORPUS[case][1], CORPUS[case][2])
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    outcome = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert (
        outcome.status is pure.Status.OK
        and outcome.canonical_bytes == product.canonical_bytes
    )
    view = pure.Inspection(outcome)
    empty = schema.Value(schema.Tag.SEQUENCE, ())
    if case == 2:
        bodies = view.for_kind("project_sql_set_body")
        assert [
            next(f.value.data for f in r.fields if f.name == "kind") for r in bodies
        ] == ["union", "except"]
        assert view.for_kind("decimal_precision_scale")
        parented = next(
            r
            for r in view.for_kind("project_row_equivalence_field")
            if next(f.value.data for f in r.fields if f.name == "parents")
        )
        mutations = [(bodies[-1], "operands", empty), (parented, "parents", empty)]
        for column in view.for_kind("project_sql_set_column"):
            mutations.append((column, "inputs", empty))
    else:
        hidden = view.for_kind("project_sql_hidden_order_requirement")[0]
        closure = view.for_kind("project_ir_output_strict_closure")[0]
        assert view.for_kind("project_ir_output_fd_proof_step")
        mutations = [
            (hidden, "proof", schema.Value(schema.Tag.ABSENT, None)),
            (closure, "witness", empty),
        ]
    for record, field, value in mutations:
        rejected = pure.evaluate_project_sql_plan_document(
            _change(product.document, record, field, value)
        )
        assert (
            rejected.status is not pure.Status.OK and rejected.canonical_bytes is None
        )


def test_group_window_qualify_and_explicit_target_vertical(tmp_path):
    verified = construction(tmp_path / "source", CORPUS[3][1], CORPUS[3][2])
    supplied = assessment(verified)
    product = portable.build_project_sql_plan_portable(verified, assessment=supplied)
    assert portable.verify_project_sql_plan_portable(
        product, verified, assessment=supplied
    ).verified
    assert not portable.verify_project_sql_plan_portable(product, verified).verified
    view = pure.Inspection(
        pure.parse_project_sql_plan_document(product.canonical_bytes)
    )
    assert view.for_kind("project_sql_aggregation")
    assert view.for_kind("project_sql_window")
    assert view.for_kind("project_sql_qualify_site")
    assert view.for_kind("project_sql_target_aspect")
    empty = schema.Value(schema.Tag.SEQUENCE, ())
    for kind, field in (
        ("project_sql_plan", "windows"),
        ("project_sql_target_assessment", "demands"),
        ("project_sql_target_demand", "aspects"),
        ("project_sql_target_summary", "pending_realizations"),
    ):
        record = view.for_kind(kind)[0]
        rejected = pure.evaluate_project_sql_plan_document(
            _change(product.document, record, field, empty)
        )
        assert (
            rejected.status is not pure.Status.OK and rejected.canonical_bytes is None
        )


def test_five_source_observation_and_single_renderer(tmp_path):
    result = observation(tmp_path / "probe")
    cases = result["cases"]
    assert isinstance(cases, list)
    assert [r["case"] for r in cases] == [r[0] for r in CORPUS]
    framed = render(result, tmp_path)
    assert framed.endswith(b"\n") and not framed.endswith(b"\n\n")
    assert json.loads(framed) == result


@pytest.mark.parametrize(
    "raw",
    [
        b'{"format":"x","format":"x"}',
        b'{"outer":{"value":1,"value":1}}',
        b'{"outer":[{"value":true,"value":false}]}',
    ],
)
def test_raw_duplicate_object_keys_reject_at_every_depth(raw):
    outcome = pure.parse_project_sql_plan_document(raw)
    assert outcome.status is pure.Status.DUPLICATE_KEY
    assert outcome.canonical_bytes is None and outcome.document is None


@pytest.mark.parametrize(
    "raw,status",
    [
        (b"\xff", pure.Status.INVALID_UTF8),
        (b"{} {}", pure.Status.INVALID_JSON),
        (b'{"x":NaN}', pure.Status.INVALID_VALUE),
        (b'{"x":Infinity}', pure.Status.INVALID_VALUE),
        (b'{"x":-Infinity}', pure.Status.INVALID_VALUE),
        (b'{"x":1e99999}', pure.Status.INVALID_VALUE),
        (b'{"format":', pure.Status.INVALID_JSON),
        (b"[" * 65 + b"]" * 65, pure.Status.RESOURCE_LIMIT),
    ],
)
def test_raw_boundary_has_closed_rejections_without_bytes(raw, status):
    outcome = pure.parse_project_sql_plan_document(raw)
    assert outcome.status is status
    assert outcome.canonical_bytes is None


def test_parsed_container_cycles_are_controlled_and_not_json_authentication():
    value = {"format": schema.FORMAT, "records": []}
    value["records"].append(value)
    outcome = pure.decode_project_sql_plan_mapping(value)
    assert outcome.status is pure.Status.INVALID_INPUT
    assert outcome.canonical_bytes is None
    # Parsing through another loader already loses duplicate-key history.
    parsed = json.loads('{"format":"x","format":"x"}')
    assert (
        pure.decode_project_sql_plan_mapping(parsed).status
        is not pure.Status.DUPLICATE_KEY
    )


def test_raw_resource_limit_precedes_json_conversion():
    outcome = pure.parse_project_sql_plan_document(b" " * (schema.MAX_BYTES + 1))
    assert outcome.status is pure.Status.RESOURCE_LIMIT
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize("value", [None, True, 0, [], {}, object()])
def test_pure_non_document_input_never_becomes_empty_success(value):
    outcome = pure.evaluate_project_sql_plan_document(value)
    assert outcome.status is pure.Status.INVALID_DOCUMENT
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize("text", ["+1", "01", "-0", "1.0", "١", " 1", "1e3"])
def test_integer_lexical_transport_is_exact(text):
    with pytest.raises(pure._Reject):
        pure._integer(text)


def test_numeric_transport_preserves_large_int_and_signed_zero():
    value = "9" * schema.MAX_DIGITS
    assert str(pure._integer(value)) == value
    assert pure._float("-0x0.0p+0").hex() == "-0x0.0p+0"
    assert pure._float("0x0.0p+0").hex() == "0x0.0p+0"
    for text in ("NaN", "inf", "-inf", "0x1p+999999", "1.0"):
        with pytest.raises(pure._Reject):
            pure._float(text)
