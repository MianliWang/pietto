"""Portable consistency and actual interpreter-cell observations."""

from dataclasses import replace
from pathlib import Path
import json

import pytest

from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    verify_project_query_block_ir,
    build_project_query_block_ir_analysis_bundle,
)
from pietto._project.project_query_block_ir_inspection import (
    build_project_query_block_ir_inspection,
)
from pietto._project import project_query_block_ir_pure_boundary as pure
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
    _source,
)
from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
    _source as set_source,
)


def _document(tmp_path: Path, source: str):
    root = build_project_query_block_ir(_completed(tmp_path, source))
    verified = verify_project_query_block_ir(root)
    assert verified.verified, verified.issues
    return build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verified)
    ).document


def _field(record, key: str, value):
    return replace(
        record,
        fields=tuple(
            replace(field, value=value) if field.key == key else field
            for field in record.fields
        ),
    )


def test_distinct_order_proof_cannot_be_erased_from_portable_document(
    tmp_path: Path,
) -> None:
    source = (
        _source("true").replace("select:", "select distinct:")
        + "    order by:\n        lhs.id\n"
    )
    document = _document(tmp_path, source)
    records = tuple(
        _field(record, "order_proofs", pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.DISTINCT
        else record
        for record in document.records
    )
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(document, records=records)
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize(
    "kind",
    (
        pure.ProjectQueryBlockIRRecordKind.CONDITION,
        pure.ProjectQueryBlockIRRecordKind.INPUT_CORRESPONDENCE,
    ),
)
def test_matching_evidence_cannot_be_silently_dropped(tmp_path: Path, kind) -> None:
    document = _document(tmp_path, _source("lhs.id == r.id"))
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(
            document,
            records=tuple(
                record for record in document.records if record.kind is not kind
            ),
        )
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize(
    "kind",
    (
        pure.ProjectQueryBlockIRRecordKind.SET_OPERAND,
        pure.ProjectQueryBlockIRRecordKind.SET_FIELD_MAP,
        pure.ProjectQueryBlockIRRecordKind.TYPE_EQUIVALENCE,
    ),
)
def test_set_maps_membership_and_types_are_required(tmp_path: Path, kind) -> None:
    document = _document(
        tmp_path, set_source("except", "all", operands=("lhs", "rhs", "rhs"))
    )
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(
            document,
            records=tuple(
                record for record in document.records if record.kind is not kind
            ),
        )
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize("value", (None, {}, [], "unknown", 0))
def test_pure_boundary_is_total_for_non_documents(value) -> None:
    result = pure.evaluate_project_query_block_ir_document(value)
    assert result.status is pure.ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT
    assert result.canonical_bytes is None


SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


def test_real_flat_ir_records_bytes_and_rejections_match_every_process_cell(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    import _pietto_differential_process_acquisition as acquisition

    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase64")
    expected_keys = {
        f"source:python{major}.{minor}:seed:{seed}"
        for major, minor in store.interpreters
        for seed in SEEDS
    }
    expected_keys.update(
        f"{mode}:python{major}.{minor}:seed:7"
        for major, minor in store.interpreters
        for mode in ("relocated", "installed")
    )
    assert set(documents) == expected_keys
    baseline = next(iter(documents.values()))
    observed = json.loads(baseline)
    assert [case["case"] for case in observed["cases"]] == [
        "proved",
        "unproved",
        "alias",
        "strict_fd",
        "v1_control",
    ]
    for document in documents.values():
        assert document == baseline
        assert json.loads(document) == observed
    installed_root = store.installed_source_root()
    installed_cells = tuple(cell for cell in store.plan if cell.mode == "installed")
    assert {cell.version for cell in installed_cells} == set(store.interpreters)
    for cell in installed_cells:
        _assert_installed_origin(
            store.import_origin(cell), installed_root, acquisition.REPO_ROOT
        )


def _assert_installed_origin(
    origin: Path, installed_root: Path, checkout: Path
) -> None:
    resolved = origin.resolve()
    assert resolved.is_relative_to((installed_root / "src" / "pietto").resolve())
    assert not resolved.is_relative_to(checkout.resolve())


def test_installed_origin_requires_exact_target_and_checkout_exclusion(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    installed = tmp_path / "installed-wheel" / "wheel-source"
    _assert_installed_origin(installed / "src/pietto/__init__.py", installed, checkout)
    for origin, target in (
        (checkout / "src/pietto/__init__.py", installed),
        (tmp_path / "unrelated/pietto/__init__.py", installed),
        (checkout / "wheel-source/src/pietto/__init__.py", checkout / "wheel-source"),
    ):
        with pytest.raises(AssertionError):
            _assert_installed_origin(origin, target, checkout)


def test_phase64_standalone_probe_matches_its_single_renderer(tmp_path: Path) -> None:
    import subprocess
    import sys
    import _pietto_phase64_flat_ir_differential_probe as probe

    expected_root = tmp_path / "api"
    expected = probe.render(probe.observation(expected_root), expected_root)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(probe.__file__).resolve()),
            "--workspace",
            str(tmp_path / "standalone"),
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert result.stderr == b""
    assert result.stdout == expected
    assert result.stdout.endswith(b"\n") and not result.stdout.endswith(b"\n\n")


@pytest.mark.parametrize(
    "member", ("scope", "references", "proof_root", "order_proof", "type_identity")
)
def test_new_portable_evidence_is_closed_and_linked(
    tmp_path: Path, member: str
) -> None:
    from _pietto_phase64_flat_ir_differential_probe import SOURCE
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import ProjectSingleMatchRequest

    completed = _completed(
        tmp_path, SOURCE.replace("on true", "on combined.id == r.id")
    )
    condition = completed.roots.join_conditions.entries[0]
    completed = with_project_single_match_requests(
        completed,
        (ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use),),
    )
    root = build_project_query_block_ir(completed)
    document = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(
            verify_project_query_block_ir(root)
        )
    ).document
    kinds = {
        "scope": pure.ProjectQueryBlockIRRecordKind.CONDITION,
        "references": pure.ProjectQueryBlockIRRecordKind.CONDITION,
        "proof_root": pure.ProjectQueryBlockIRRecordKind.PROOF,
        "order_proof": pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF,
        "type_identity": pure.ProjectQueryBlockIRRecordKind.TYPE_EQUIVALENCE,
    }
    record = next(record for record in document.records if record.kind is kinds[member])
    if member == "scope":
        changed = _field(
            record,
            "scope",
            pure.project_query_block_ir_pure_enumeration("unrelated_scope"),
        )
    elif member == "references":
        changed = _field(record, "references", pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT)
    elif member == "proof_root":
        changed = _field(
            record,
            "roots",
            pure.project_query_block_ir_pure_texts(('{"kind":"foreign_root"}',)),
        )
    elif member == "order_proof":
        changed = _field(record, "visible", pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT)
    else:
        original = next(
            field.value.text for field in record.fields if field.key == "capability"
        )
        assert original is not None
        data = json.loads(original)
        data["selected"] = {}
        changed = _field(
            record,
            "capability",
            pure.project_query_block_ir_pure_text(json.dumps(data)),
        )
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(
            document,
            records=tuple(
                changed if item is record else item for item in document.records
            ),
        )
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize(
    "component", ("kind", "owner", "field_position", "name", "final_kind")
)
def test_capability_locator_and_canonical_final_roles_are_bound(
    tmp_path: Path, component: str
) -> None:
    from test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin import (
        _source as distinct_source,
    )

    document = _document(tmp_path, distinct_source())
    if component == "final_kind":
        record = next(
            r
            for r in document.records
            if r.kind is pure.ProjectQueryBlockIRRecordKind.ROW_FIELD
            and next(
                f.value.enumeration for f in r.fields if f.key == "semantic_source_kind"
            )
            == "ProjectCompletedOutputField"
            and next(f.value.enumeration for f in r.fields if f.key == "final_kind")
            == "relation_output"
        )
        changed = _field(
            record,
            "final_kind",
            pure.project_query_block_ir_pure_enumeration("source_field"),
        )
    else:
        record = next(
            r
            for r in document.records
            if r.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_EQUIVALENCE
        )
        encoded = next(f.value.text for f in record.fields if f.key == "capability")
        assert encoded is not None
        data = json.loads(encoded)
        if component == "owner":
            data["selected"]["owner"]["identity"]["declared_name"] = "rows"
        else:
            data["selected"][component] = {
                "kind": "shape_field",
                "field_position": 1,
                "name": "other",
            }[component]
        changed = _field(
            record,
            "capability",
            pure.project_query_block_ir_pure_text(json.dumps(data)),
        )
    result = pure.evaluate_project_query_block_ir_document(
        replace(
            document,
            records=tuple(changed if r is record else r for r in document.records),
        )
    )
    assert result.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert result.canonical_bytes is None


def _order_source(mode: str) -> str:
    from test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin import (
        _source as distinct_source,
    )

    if mode == "composed_fd":
        return (
            _source("true")
            .replace(
                "allow_any: Bool nullable",
                "allow_any: Bool nullable\n    unique by_id on id",
            )
            .replace("select:", "select distinct:")
            + "        right_id = r.id\n    order by:\n        r.key\n"
        )
    if mode == "strict_fd":
        return (
            distinct_source().replace(
                "value: Int nullable",
                "value: Int not null\n    unique by_value on value",
            )
            + "    order by:\n        hidden\n"
        )
    return (
        distinct_source().replace("hidden: Float nullable", "hidden: Int nullable")
        + "        hidden\n    order by:\n        value\n        hidden\n"
    )


def _value(record, key):
    return next(field.value for field in record.fields if field.key == key)


@pytest.mark.parametrize("mode", ("visible", "strict_fd", "composed_fd"))
def test_order_proof_variants_retain_declared_bindings_and_supplied_steps(
    tmp_path: Path, mode: str
) -> None:
    document = _document(tmp_path, _order_source(mode))
    proofs = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF
    )
    bindings = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_BINDING
    )
    assert len(proofs) == len(bindings) == (2 if mode == "visible" else 1)
    for proof, binding in zip(proofs, bindings, strict=True):
        assert _value(proof, "binding") == _value(binding, "ref")
        assert _value(proof, "mode").enumeration == (
            "visible" if mode == "visible" else "strict_fd"
        )
        if mode == "visible":
            assert len(_value(proof, "visible").refs) == 2
            assert len(_value(proof, "targets").refs) == 1
        else:
            assert _value(proof, "property").ref is not None
            assert _value(proof, "seed").refs and _value(proof, "requested").refs
            assert _value(proof, "steps").texts


@pytest.mark.parametrize(
    "mutation", ("missing", "empty", "swap", "variant", "property", "seed", "fd_step")
)
def test_order_binding_and_witness_corruptions_are_rejected(
    tmp_path: Path, mutation: str
) -> None:

    mode = (
        "visible"
        if mutation in {"missing", "empty", "swap", "variant"}
        else "strict_fd"
    )
    document = _document(tmp_path, _order_source(mode))
    proofs = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF
    )
    proof = proofs[0]
    if mutation == "missing":
        records = tuple(r for r in document.records if r is not proof)
    else:
        if mutation == "empty":
            key, value = "targets", pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
        elif mutation == "swap":
            key, value = "targets", _value(proofs[1], "targets")
        elif mutation == "variant":
            key, value = (
                "mode",
                pure.project_query_block_ir_pure_enumeration("strict_fd"),
            )
        elif mutation == "property":
            key = "property"
            value = next(
                _value(r, "ref")
                for r in document.records
                if r.kind is pure.ProjectQueryBlockIRRecordKind.RELATIONAL_PROPERTY
                and _value(r, "ref") != _value(proof, "property")
            )
        elif mutation == "seed":
            key, value = "seed", _value(proof, "requested")
        else:
            key = "steps"
            data = json.loads(_value(proof, key).texts[0])
            data["fact"] = 10**6
            value = pure.project_query_block_ir_pure_texts((json.dumps(data),))
        altered = _field(proof, key, value)
        records = tuple(altered if r is proof else r for r in document.records)
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(document, records=records)
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


def _json_record(record, key):
    text = _value(record, key).text
    assert text is not None
    return json.loads(text)


def _decimal_source(mode: str, tmp_path: Path) -> str:
    from test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin import (
        _source as distinct_source,
    )

    if mode == "direct":
        return distinct_source("Decimal(10, 2)")
    if mode == "imported":
        (tmp_path / "types.pietto").write_text(
            "type Base = Decimal(10, 2)\nexport:\n    type Base\n"
        )
        (tmp_path / "facade.pietto").write_text(
            'import "types.pietto":\n    type Base as Public\nexport:\n    type Public\n'
        )
        return 'import "facade.pietto":\n    type Public as Alias\n' + distinct_source(
            "Alias"
        )
    source = "type Base = Decimal(10, 2)\ntype Alias = Base\n" + distinct_source(
        "Alias"
    )
    if mode in {"inherited", "repeated"}:
        source = source.replace("query result:", "table dedup:")
        source += (
            "table combined:\n    union all:\n        from dedup\n        from dedup\n"
        )
        source += (
            "query result:\n    from combined\n    select distinct:\n        value\n"
            if mode == "inherited"
            else "query result:\n    union all:\n        from combined\n        from combined\n"
        )
    return source


@pytest.mark.parametrize(
    "mode", ("direct", "alias", "imported", "inherited", "repeated")
)
def test_decimal_sources_and_parent_references_are_retained(
    tmp_path: Path, mode: str
) -> None:

    document = _document(tmp_path, _decimal_source(mode, tmp_path))
    capabilities = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_EQUIVALENCE
    )
    sources = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_PARAMETER_SOURCE
    )
    assert sources
    declared = {_value(r, "ref").ref: r for r in (*capabilities, *sources)}
    for capability in capabilities:
        source_ref = _value(capability, "parameter_source").ref
        parents = _value(capability, "parents").refs
        if parents:
            assert source_ref is None
            assert all(parent in declared for parent in parents)
        else:
            assert source_ref is not None
            source = declared[source_ref]
            assert _value(source, "capability") == _value(capability, "ref")
            assert _value(source, "parameters").integers == (10, 2)
            assert _json_record(source, "site")["path"] == (
                "types.pietto" if mode == "imported" else "main.pietto"
            )
    if mode in {"inherited", "repeated"}:
        roots = tuple(r for r in capabilities if _value(r, "parents").refs)
        assert len(roots) == (1 if mode == "inherited" else 2)
        if mode == "repeated":
            assert _value(roots[0], "ref") != _value(roots[1], "ref")
        for root in roots:
            selected = _json_record(root, "capability")["selected"]
            for parent in _value(root, "parents").refs:
                original = _json_record(declared[parent], "capability")["selected"]
                assert original["owner"] != selected["owner"]


@pytest.mark.parametrize(
    "mutation",
    ("missing_source", "missing_parent", "source_swap", "alias", "parameters"),
)
def test_decimal_source_and_parent_corruptions_are_rejected(
    tmp_path: Path, mutation: str
) -> None:

    document = _document(tmp_path, _decimal_source("inherited", tmp_path))
    capabilities = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_EQUIVALENCE
    )
    sources = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_PARAMETER_SOURCE
    )
    if mutation == "missing_source":
        records = tuple(r for r in document.records if r is not sources[0])
    else:
        if mutation == "missing_parent":
            target = next(r for r in capabilities if _value(r, "parents").refs)
            replacement = _field(
                target, "parents", pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
            )
        elif mutation == "source_swap":
            target = next(
                r for r in capabilities if _value(r, "parameter_source").ref is not None
            )
            source = next(
                r
                for r in sources
                if _value(r, "ref") != _value(target, "parameter_source")
            )
            replacement = _field(target, "parameter_source", _value(source, "ref"))
        elif mutation == "alias":
            target = sources[0]
            data = _json_record(target, "owner")
            data["identity"]["declared_name"] = "WrongBase"
            replacement = _field(
                target, "owner", pure.project_query_block_ir_pure_text(json.dumps(data))
            )
        else:
            target = sources[0]
            replacement = _field(
                target, "parameters", pure.project_query_block_ir_pure_integers((10, 3))
            )
        records = tuple(replacement if r is target else r for r in document.records)
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(document, records=records)
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


def test_convergence_rereview_order_source_uses_its_actual_module(
    tmp_path: Path,
) -> None:
    (tmp_path / "rows.pietto").write_text(
        'shape Row:\n    value: Int nullable\nsource rows: Row is postgres.table("rows")\nexport:\n    source rows\n'
    )
    source = 'import "rows.pietto":\n    source rows\nquery result:\n    from rows\n    select distinct:\n        value\n    order by:\n        value\n'
    document = _document(tmp_path, source)
    record = next(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_SOURCE
    )
    assert _json_record(record, "site")["path"] == "rows.pietto"


def test_convergence_rereview_fd_property_must_be_an_actual_input(
    tmp_path: Path,
) -> None:
    source = _order_source("strict_fd").replace(
        'source rows: Row is postgres.table("rows")',
        'source rows: Row is postgres.table("rows")\nsource other: Row is postgres.table("other")',
    )
    document = _document(tmp_path, source)
    declared = {
        _value(r, "ref").ref: r
        for r in document.records
        if any(f.key == "ref" for f in r.fields)
    }
    other = next(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
        and _value(r, "declared_name").text == "other"
    )
    prop_value = _value(other, "active_property")
    prop = declared[prop_value.ref]
    classes = _value(prop, "value_classes").refs
    assert len(classes) == 2
    fact_ref = _value(prop, "value_fds").refs[0]
    fact = declared[fact_ref]
    assert _value(fact, "determinants").refs == classes[:1]
    assert _value(fact, "dependents").refs == classes[1:]
    records = []
    for record in document.records:
        if record.kind in {
            pure.ProjectQueryBlockIRRecordKind.ORDER_BINDING,
            pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF,
        }:
            record = _field(record, "property", prop_value)
            record = _field(
                record, "seed", pure.project_query_block_ir_pure_refs(classes[:1])
            )
            record = _field(
                record, "requested", pure.project_query_block_ir_pure_refs(classes[1:])
            )
            if record.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF:
                record = _field(
                    record, "closure", pure.project_query_block_ir_pure_refs(classes)
                )
                record = _field(
                    record,
                    "steps",
                    pure.project_query_block_ir_pure_texts(
                        (
                            json.dumps(
                                {
                                    "fact": fact_ref.position,
                                    "derived": [classes[1].position],
                                }
                            ),
                        )
                    ),
                )
        records.append(record)
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(document, records=tuple(records))
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize("mutation", ("role", "span"))
def test_convergence_rereview_decimal_source_metadata_is_closed(
    tmp_path: Path, mutation: str
) -> None:
    document = _document(tmp_path, _decimal_source("direct", tmp_path))
    source = next(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_PARAMETER_SOURCE
    )
    if mutation == "role":
        capability = next(
            r
            for r in document.records
            if r.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_EQUIVALENCE
        )
        data = _json_record(capability, "capability")
        data["declaration_role"] = "unknown_role"
        changed_capability = _field(
            capability,
            "capability",
            pure.project_query_block_ir_pure_text(json.dumps(data)),
        )
        changed_source = _field(
            source, "role", pure.project_query_block_ir_pure_enumeration("unknown_role")
        )
        records = tuple(
            changed_capability
            if r is capability
            else changed_source
            if r is source
            else r
            for r in document.records
        )
    else:
        site = _json_record(source, "site")
        site["line"] = 0
        changed_source = _field(
            source, "site", pure.project_query_block_ir_pure_text(json.dumps(site))
        )
        records = tuple(changed_source if r is source else r for r in document.records)
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(document, records=records)
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


def test_visible_order_preserves_repeated_target_occurrences(tmp_path: Path) -> None:
    from test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin import (
        _source as distinct_source,
    )

    document = _document(
        tmp_path, distinct_source() + "    order by:\n        value + value\n"
    )
    proof = next(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF
    )
    visible, targets = _value(proof, "visible").refs, _value(proof, "targets").refs
    assert len(visible) == 1 and targets == (visible[0], visible[0])
    assert (
        pure.evaluate_project_query_block_ir_document(document).status
        is pure.ProjectQueryBlockIRPureStatus.OK
    )


def test_set_canonical_output_cannot_take_a_source_field_role(tmp_path: Path) -> None:
    document = _document(tmp_path, set_source())
    record = next(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.ROW_FIELD
        and _value(r, "semantic_source_kind").enumeration
        == "ProjectCompletedSetOutputField"
    )
    replacement = _field(
        record,
        "final_kind",
        pure.project_query_block_ir_pure_enumeration("source_field"),
    )
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(
            document,
            records=tuple(replacement if r is record else r for r in document.records),
        )
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


def _join_producer_source(form: str) -> str:
    source = _source("lhs.id == r.id")
    if form == "historical":
        return _source(None).replace("select:", "select distinct:")
    if form == "self":
        return source.replace("join rhs as r:", "join lhs as r:")
    if form == "completed":
        from test_phase64_slice10_project_ir_composition_verification_invalidation_inspection_pure_boundary import (
            _vertical_source,
        )

        return _vertical_source("left", "right")
    if form == "set":
        return (
            set_source()
            + """query joined:
    from combined
    semi join combined as r:
        from combined
        on combined.id == r.id
    select:
        id = combined.id
"""
        )
    if form == "accumulated":
        return source.replace(
            "    select:\n",
            """    left join rhs as s:
        from lhs
        on r.id == s.id
    full join rhs as t:
        from lhs
        on s.id == t.id
    select:
""",
        )
    assert form == "direct"
    return source


@pytest.mark.parametrize(
    "form", ("direct", "historical", "self", "completed", "set", "accumulated")
)
def test_join_producer_correspondence_retains_valid_inputs_and_rejects_omission(
    tmp_path: Path, form: str
) -> None:
    document = _document(tmp_path, _join_producer_source(form))
    original = pure.evaluate_project_query_block_ir_document(document)
    assert original.status is pure.ProjectQueryBlockIRPureStatus.OK
    assert original.canonical_bytes is not None
    inputs = tuple(
        r
        for r in document.records
        if r.kind is pure.ProjectQueryBlockIRRecordKind.INPUT_CORRESPONDENCE
    )
    assert inputs
    internal = tuple(r for r in inputs if _value(r, "producer").ref is None)
    assert len(internal) == (2 if form == "accumulated" else 0)
    if form in {"self", "set"}:
        left, right = inputs[-2:]
        assert _value(left, "producer") == _value(right, "producer")
        assert _value(left, "use") != _value(right, "use")
    for image in inputs:
        if _value(image, "producer").ref is None:
            continue
        changed = _field(image, "producer", pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT)
        outcome = pure.evaluate_project_query_block_ir_document(
            replace(
                document,
                records=tuple(changed if r is image else r for r in document.records),
            )
        )
        assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
        assert outcome.canonical_bytes is None
    assert pure.evaluate_project_query_block_ir_document(document) == original


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_owner",
        "wrong_output",
        "dangling",
        "wrong_domain",
        "terminal",
        "use_owner",
    ),
)
def test_join_external_producer_links_fail_closed(
    tmp_path: Path, mutation: str
) -> None:
    document = _document(tmp_path, _join_producer_source("direct"))
    assert pure.evaluate_project_query_block_ir_document(document).canonical_bytes
    kind = pure.ProjectQueryBlockIRRecordKind
    images = tuple(r for r in document.records if r.kind is kind.INPUT_CORRESPONDENCE)
    left, image = images
    producer = _value(image, "producer")
    owner = next(
        r
        for r in document.records
        if r.kind is kind.OWNER_ENTRY and _value(r, "ref") == producer
    )
    changes = []
    if mutation == "wrong_owner":
        changes.append((image, _field(image, "producer", _value(left, "producer"))))
    elif mutation == "wrong_output":
        changes.append((image, _field(image, "output", _value(left, "output"))))
    elif mutation == "dangling":
        assert producer.ref is not None
        changes.append(
            (
                image,
                _field(
                    image,
                    "producer",
                    pure.project_query_block_ir_pure_ref(
                        replace(producer.ref, position=999999)
                    ),
                ),
            )
        )
    elif mutation == "wrong_domain":
        changes.append((image, _field(image, "producer", _value(image, "output"))))
    elif mutation == "terminal":
        changed = _field(
            owner, "variant", pure.project_query_block_ir_pure_enumeration("terminal")
        )
        for key in ("active_output", "active_property"):
            changed = _field(changed, key, pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT)
        changed = _field(
            changed,
            "terminal_reason",
            pure.project_query_block_ir_pure_enumeration(
                "semantic_output_non_concrete"
            ),
        )
        changed = _field(
            changed,
            "blocker_kind",
            pure.project_query_block_ir_pure_enumeration(
                "ProjectEffectiveOutputTerminal"
            ),
        )
        changes.append((owner, changed))
    else:
        use = next(
            r
            for r in document.records
            if r.kind is kind.USE and _value(r, "ref") == _value(image, "use")
        )
        changes.append((use, _field(use, "owner", producer)))
    records = tuple(
        next((new for old, new in changes if r is old), r) for r in document.records
    )
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(document, records=records)
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize(
    "mutation",
    (
        "external",
        "non_predecessor",
        "self",
        "forward",
        "other_owner",
        "right_internal",
        "populated_internal",
    ),
)
def test_join_internal_exemption_requires_the_actual_prefix(
    tmp_path: Path, mutation: str
) -> None:
    source = _join_producer_source("accumulated")
    source += "query other:" + source.split("query result:", 1)[1]
    document = _document(tmp_path, source)
    assert pure.evaluate_project_query_block_ir_document(document).canonical_bytes
    kind = pure.ProjectQueryBlockIRRecordKind
    joins = tuple(r for r in document.records if r.kind is kind.ALGEBRA)
    assert len(joins) == 6
    images = tuple(r for r in document.records if r.kind is kind.INPUT_CORRESPONDENCE)
    image = images[4]
    incoming = _value(image, "output")
    producer = pure.PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
    if mutation == "external":
        incoming = _value(images[0], "output")
    elif mutation == "non_predecessor":
        incoming = _value(joins[0], "output")
    elif mutation == "self":
        incoming = _value(joins[2], "output")
    elif mutation == "forward":
        image = images[2]
        incoming = _value(joins[2], "output")
    elif mutation == "other_owner":
        incoming = _value(joins[4], "output")
    elif mutation == "right_internal":
        image = images[5]
    else:
        producer = _value(images[0], "producer")
    use = next(
        r
        for r in document.records
        if r.kind is kind.USE and _value(r, "ref") == _value(image, "use")
    )
    changed_image = _field(_field(image, "producer", producer), "output", incoming)
    changed_use = _field(use, "output", incoming)
    outcome = pure.evaluate_project_query_block_ir_document(
        replace(
            document,
            records=tuple(
                changed_image if r is image else changed_use if r is use else r
                for r in document.records
            ),
        )
    )
    assert outcome.status is not pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes is None
