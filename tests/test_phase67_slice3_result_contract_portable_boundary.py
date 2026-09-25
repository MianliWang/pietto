"""Real neutral contracts, closed data-only grammar, and independent negatives."""

from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_result_contract as c
from pietto._project import project_result_contract_pure_boundary as pure
from pietto._project import project_result_contract_portable as writer
from pietto._project import project_result_contract_correspondence as runtime


@pytest.fixture(scope="module")
def contracts(tmp_path_factory):
    root = tmp_path_factory.mktemp("contract-documents")
    return {name: probe.contract_fixture(root, name) for name in probe.CONTRACT_CORPUS}


@pytest.mark.parametrize("name", probe.CONTRACT_CORPUS)
def test_complete_neutral_export_and_independent_expected_fields(contracts, name):
    checked, contract = contracts[name]
    exported = writer.export_result_contract(contract, checked)
    runtime.verify_bound_export(exported, checked)
    view = probe.check_document_oracle(name, exported.canonical_bytes.decode("utf-8"))
    assert pure.reencode_contract(view) == exported.canonical_bytes
    assert (
        writer.export_result_contract(contract, checked).canonical_bytes
        == exported.canonical_bytes
    )
    assert "pyarrow" not in sys.modules
    owned = view.fields
    owned[0]["label"] = "changed"
    assert view.fields[0]["label"] != "changed"


def test_pure_valid_coherent_substitutions_require_external_denominator(contracts):
    checked, contract = contracts["postgres"]
    exported = writer.export_result_contract(contract, checked)
    smaller = probe.coherent_tail(exported.view)
    assert len(smaller.fields) == 1
    with pytest.raises(c.ResultError, match="CORRESPONDENCE"):
        runtime.verify_contract_correspondence(smaller, contract, checked)
    doc = exported.view.document
    doc["fields"][0]["nullability"] = "unknown"
    changed = pure.decode_contract(pure.encode_document(doc))
    with pytest.raises(c.ResultError, match="CORRESPONDENCE"):
        runtime.verify_contract_correspondence(changed, contract, checked)
    checked, contract = contracts["descriptors"]
    doc = writer.export_result_contract(contract, checked).view.document
    doc["ordering"]["keys"][0].update(authored_direction="asc", direction="asc")
    changed = pure.decode_contract(pure.encode_document(doc))
    with pytest.raises(c.ResultError, match="CORRESPONDENCE"):
        runtime.verify_contract_correspondence(changed, contract, checked)


def test_independent_checker_detects_coherent_writer_defect(contracts, monkeypatch):
    checked, contract = contracts["postgres"]
    exported = writer.export_result_contract(contract, checked)
    smaller = probe.coherent_tail(exported.view)
    monkeypatch.setattr(writer._Projection, "document", lambda *args: smaller.document)
    defective = writer.export_result_contract(contract, checked)
    with pytest.raises(c.ResultError, match="CORRESPONDENCE"):
        runtime.verify_bound_export(defective, checked)
    monkeypatch.setattr(
        writer, "export_result_contract", lambda *args: pytest.fail("writer called")
    )
    monkeypatch.setattr(
        writer._Projection, "document", lambda *args: pytest.fail("projection called")
    )
    runtime.verify_bound_export(exported, checked)


def test_explicit_foreign_context_relocation_and_original_continuity(
    contracts, tmp_path
):
    checked, contract = contracts["postgres"]
    other_checked, other_contract = probe.contract_fixture(tmp_path, "postgres")
    first = writer.export_result_contract(contract, checked)
    second = writer.export_result_contract(other_contract, other_checked)
    assert first.canonical_bytes == second.canonical_bytes
    with pytest.raises(c.ResultError, match="ROOT"):
        runtime.verify_bound_export(first, other_checked)
    with pytest.raises(c.ResultError, match="ROOT"):
        writer.export_result_contract(contract, other_checked)
    runtime.verify_contract_correspondence(first.view, other_contract, other_checked)
    runtime.verify_bound_export(first, checked)


@pytest.mark.parametrize(
    "part",
    ("owner", "output", "port", "canonical", "declared", "provenance", "nullability"),
)
def test_runtime_grafts_and_saved_bytes_are_distinct(contracts, part):
    checked, contract = contracts["postgres"]
    exported = writer.export_result_contract(contract, checked)
    if part in ("owner", "output"):
        bad = replace(contract, **{part: object()})
    else:
        leaf = contract.shape.fields[0]
        if part in ("canonical", "declared"):
            leaf = replace(leaf, shape=replace(leaf.shape, **{part: object()}))
        else:
            leaf = replace(leaf, **{part: object()})
        bad = replace(contract, shape=c.ResultShape((leaf, *contract.shape.fields[1:])))
    pure.decode_contract(exported.canonical_bytes)
    with pytest.raises(c.ResultError):
        writer.export_result_contract(bad, checked)
    with pytest.raises(c.ResultError):
        runtime.verify_contract_correspondence(exported.view, bad, checked)


@pytest.mark.parametrize(
    "damage",
    (
        "version",
        "extra",
        "missing",
        "kind",
        "bool",
        "drop",
        "duplicate",
        "reorder",
        "dangling",
        "foreign_kind",
        "cycle",
        "unreachable",
    ),
)
def test_closed_document_shape_and_reference_invariants(contracts, damage):
    checked, contract = contracts["descriptors"]
    doc = writer.export_result_contract(contract, checked).view.document
    if damage == "version":
        doc["format"] += ".next"
    elif damage == "extra":
        doc["extra"] = 1
    elif damage == "missing":
        del doc["multiplicity"]
    elif damage == "kind":
        doc["fields"][0]["canonical"]["kind"] = "shape"
    elif damage == "bool":
        doc["fields"][0]["ordinal"] = False
    elif damage == "drop":
        doc["fields"].pop()
    elif damage == "duplicate":
        doc["fields"][1] = doc["fields"][0]
    elif damage == "reorder":
        doc["fields"].reverse()
    elif damage == "dangling":
        doc["fields"][2]["type_resolution"]["aliases"][0]["index"] = 99
    elif damage == "foreign_kind":
        doc["fields"][2]["type_resolution"]["aliases"][0]["kind"] = "port"
    elif damage == "cycle":
        refs = doc["fields"][2]["type_resolution"]["aliases"]
        refs.append(refs[0])
    else:
        doc["types"].append({**doc["types"][0], "id": 2})
    with pytest.raises(pure.ContractDocumentError):
        pure.encode_document(doc)


@pytest.mark.parametrize(
    "damage",
    (
        "utf8",
        "escape",
        "duplicate",
        "float",
        "nan",
        "negative_zero",
        "trailing",
        "truncate",
        "space",
        "depth",
    ),
)
def test_raw_boundary_rejects_before_canonical_acceptance(contracts, damage):
    checked, contract = contracts["postgres"]
    data = writer.export_result_contract(contract, checked).canonical_bytes
    bad = {
        "utf8": b"\xff",
        "escape": b'{"x":"\\ud800"}',
        "duplicate": b'{"format":1,"format":2}',
        "float": b'{"x":1.0}',
        "nan": b'{"x":NaN}',
        "negative_zero": b'{"x":-0}',
        "trailing": data + b"{}",
        "truncate": data[:-2],
        "space": b" " + data,
        "depth": b"[" * 49 + b"]" * 49,
    }[damage]
    with pytest.raises(pure.ContractDocumentError):
        pure.decode_contract(bad)


@pytest.mark.parametrize(
    "setting", ("bytes", "depth", "values", "records", "text", "total_text", "fields")
)
def test_small_document_limits_cover_export_decode_and_never_relax(contracts, setting):
    checked, contract = contracts["postgres"]
    data = writer.export_result_contract(contract, checked).canonical_bytes
    small = replace(pure.DocumentLimits(), **{setting: 1})
    with pytest.raises(c.ResultError, match="DOCUMENT_LIMIT"):
        writer.export_result_contract(contract, checked, limits=small)
    with pytest.raises(pure.ContractDocumentError, match="LIMIT"):
        pure.decode_contract(data, limits=small)
    larger = replace(pure.DocumentLimits(), **{setting: 10**9})
    assert getattr(pure.limits_for(larger), setting) == getattr(
        pure.DocumentLimits(), setting
    )


def test_fresh_arrow_free_data_only_process(contracts):
    documents = {
        name: writer.export_result_contract(contract, checked).canonical_bytes.decode(
            "utf-8"
        )
        for name, (checked, contract) in contracts.items()
    }
    actual = probe.pure_child(documents)
    assert actual["postgres"] == ["renamed", "other"]
    assert actual["imported"] == ["id", "label", "amount", "second"]


def test_new_runtime_boundary_has_no_reconstruction(contracts, monkeypatch):
    checked, contract = contracts["postgres"]
    for module, name in (
        ("pietto._project.check", "check_project_parse_only"),
        ("pietto._project.project_sql_plan", "build_project_sql_plan"),
        ("pietto._project.project_sql_emission", "emit_project_sql"),
    ):
        monkeypatch.setattr(
            module + "." + name, lambda *a, **k: pytest.fail("reconstructed")
        )
    runtime.verify_bound_export(
        writer.export_result_contract(contract, checked), checked
    )


def test_private_format_is_not_public_or_a_scalar_solver():
    import pietto

    assert not hasattr(pietto, "ContractView")
    assert pure.__all__ == ()
    source = Path(pure.__file__).read_text()
    assert "from pietto" not in source and "import pietto" not in source
    assert (
        json.loads(probe.emission_input("postgres"))["target"]["family"] == "postgres"
    )


def test_saved_bytes_survive_live_damage_but_bound_consumer_does_not(contracts):
    checked, contract = contracts["postgres"]
    exported = writer.export_result_contract(contract, checked)
    leaf = contract.shape.fields[0]
    previous = leaf.label
    try:
        object.__setattr__(leaf, "label", "changed")
        pure.decode_contract(exported.canonical_bytes)
        with pytest.raises(c.ResultError, match="FIELD"):
            runtime.verify_bound_export(exported, checked)
        doc = exported.view.document
        doc["fields"][0]["label"] = doc["fields"][0]["identity"]["name"] = "changed"
        alternative = pure.decode_contract(pure.encode_document(doc))
        with pytest.raises(c.ResultError, match="FIELD"):
            runtime.verify_contract_correspondence(alternative, contract, checked)
    finally:
        object.__setattr__(leaf, "label", previous)
    runtime.verify_bound_export(exported, checked)


def test_parameterized_descriptor_and_existing_enum_boundary(tmp_path):
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _roots,
    )
    from pietto._project.project_sql_plan import (
        build_project_sql_plan,
        ProjectSQLPlanUnavailable,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    source = probe.source("postgres").replace(
        "id: Int not null", "id: Decimal(18, 4) not null"
    )
    checked = probe.build_neutral(tmp_path / "decimal", {"main.pietto": source})
    contract = c.build_result_contract(checked)
    exported = writer.export_result_contract(contract, checked)
    runtime.verify_bound_export(exported, checked)
    assert [
        a["value"]["value"] for a in exported.view.fields[0]["declared"]["arguments"]
    ] == ["18", "4"]
    # This specific Enum program lacks a verified neutral plan; this is not an enum-wide claim.
    enum_source = "enum Status:\n    active\n    inactive\n" + probe.source(
        "postgres"
    ).replace("id: Int not null", "id: Status nullable")
    directory = tmp_path / "enum"
    directory.mkdir()
    args = _roots(directory, enum_source)
    plan = build_project_sql_plan(*args)
    assert isinstance(plan, ProjectSQLPlanUnavailable)
    assert [b.kind.value for b in plan.blockers] == ["expression_evidence_unavailable"]
    checked = verify_project_sql_plan(plan, *args)
    assert not checked.verified
    with pytest.raises(c.ResultError, match="ROOT"):
        c.build_result_contract(checked)


def test_equivalent_file_construction_order_and_reference_limit(contracts, tmp_path):
    checked, contract = contracts["imported"]
    expected = writer.export_result_contract(contract, checked)
    sources = dict(reversed(tuple(probe.descriptor_sources(True).items())))
    other = probe.build_neutral(tmp_path / "reversed", sources)
    actual = writer.export_result_contract(c.build_result_contract(other), other)
    assert actual.canonical_bytes == expected.canonical_bytes
    with pytest.raises(c.ResultError, match="DOCUMENT_LIMIT"):
        writer.export_result_contract(
            contract, checked, limits=pure.DocumentLimits(references=0)
        )
    with pytest.raises(pure.ContractDocumentError, match="LIMIT"):
        pure.decode_contract(
            expected.canonical_bytes, limits=pure.DocumentLimits(references=0)
        )


def test_installed_malformed_manifest_is_executable_without_arrow(contracts):
    documents = {
        name: writer.export_result_contract(contract, checked).canonical_bytes.decode(
            "utf-8"
        )
        for name, (checked, contract) in contracts.items()
    }
    assert probe.malformed_contract_cases(documents) == probe.MALFORMED_EXPECTED


def test_preflight_values_and_records_do_not_enter_json_decoder(monkeypatch):
    monkeypatch.setattr(
        pure.json,
        "loads",
        lambda *a, **k: pytest.fail("allocated JSON beyond preflight"),
    )
    for data, limits in (
        (b"[0,0,0]", pure.DocumentLimits(values=2)),
        (b'{"x":{}}', pure.DocumentLimits(records=1)),
    ):
        with pytest.raises(pure.ContractDocumentError, match="LIMIT"):
            pure.decode_contract(data, limits=limits)


def test_grouped_type_provenance_and_order_uses_cannot_lose_members(contracts):
    checked, contract = contracts["imported"]
    exported = writer.export_result_contract(contract, checked)
    doc = exported.view.document
    assert doc["ordering"]["keys"][0]["prepared"]["uses"]
    assert doc["fields"][2]["type_resolution"]["origins"][0]["paths"][0]["hops"]
    # Coherent omission has no external denominator in the pure layer.
    doc["ordering"]["keys"][0]["prepared"]["uses"] = []
    alternate = pure.decode_contract(pure.encode_document(doc))
    with pytest.raises(c.ResultError, match="CORRESPONDENCE"):
        runtime.verify_contract_correspondence(alternate, contract, checked)


def test_document_limit_is_not_the_arrow_field_limit(tmp_path):
    fields = "\n".join(f"    value{i}: Int not null" for i in range(65))
    projection = "\n".join(f"        value{i}" for i in range(65))
    source = f'shape Row:\n{fields}\nsource rows: Row is postgres.table("rows")\ntable result:\n    from rows\n    select:\n{projection}\n'
    checked = probe.build_neutral(tmp_path / "many-fields", {"main.pietto": source})
    contract = c.build_result_contract(checked)
    exported = writer.export_result_contract(contract, checked)
    assert len(exported.view.fields) == 65
    assert len(exported.canonical_bytes) < pure.DocumentLimits().bytes // 4
    runtime.verify_bound_export(exported, checked)
    with pytest.raises(c.ResultError, match="DOCUMENT_LIMIT"):
        writer.export_result_contract(
            contract, checked, limits=pure.DocumentLimits(fields=64)
        )
    c.verify_result_contract(contract, checked)
