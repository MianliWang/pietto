"""Actual source meaning acquisition precedes private physical result adaptation."""

from dataclasses import replace
from copy import copy
import importlib.util
import json

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_scalar_meaning as meaning
from pietto._project import project_result_contract as contract
from pietto._project.project_sql_emission import emit_project_sql
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)


@pytest.fixture(scope="module")
def roots(tmp_path_factory):
    root = tmp_path_factory.mktemp("scalar-meaning-roots")
    return {
        target: probe.temporal_premise(root / target, target)
        for target in ("postgres", "mysql")
    }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_actual_builtin_meaning_and_default_missing_compatibility(roots, target):
    checked, bundle, artifact, neutral = roots[target]
    meaning.verify_scalar_meaning(bundle, checked)
    assert [e.canonical.name for e in bundle.entries] == [
        "Timestamp",
        "Timestamp",
        "UUID",
        "UUID",
    ]
    assert all(
        e.source_port is p
        for e, p in zip(bundle.entries, checked.plan.source_ports, strict=True)
    )
    assert artifact.request.scalar_meaning is neutral.scalar_meaning is bundle
    assert [f.meaning for f in neutral.shape.fields] == list(bundle.entries)
    assert verify_project_sql_emission(artifact, artifact.request).verified
    for f in artifact.request.sources[0].fields:
        assert f.scalar_meaning is bundle
    old = emit_project_sql(checked, probe.temporal_input(target))
    assert old.status == "BLOCKED" and old.artifact is None
    assert [(b.code, b.detail) for b in old.blockers] == [
        ("PIE-B1004", "logical_temporal_or_uuid_meaning_missing")
    ] * 4
    generic = contract.build_result_contract(checked)
    assert generic.scalar_meaning is None and all(
        f.meaning is None for f in generic.shape.fields
    )
    assert importlib.util.find_spec("pyarrow") is None


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_source_reuse_does_not_collapse_output_occurrences(tmp_path, target):
    checked, bundle, artifact, neutral = probe.temporal_premise(
        tmp_path / "reuse", target, projection=(2, 0, 2, 1, 3)
    )
    assert [f.label for f in neutral.shape.fields] == [
        f"selected_{i}" for i in range(5)
    ]
    assert [f.meaning for f in neutral.shape.fields] == [
        bundle.entries[i] for i in (2, 0, 2, 1, 3)
    ]
    assert neutral.shape.fields[0] is not neutral.shape.fields[2]
    assert neutral.shape.fields[0].port is not neutral.shape.fields[2].port
    assert verify_project_sql_emission(artifact, artifact.request).verified
    contract.verify_result_contract(neutral, checked)


@pytest.mark.parametrize(
    "damage",
    (
        "root",
        "tail",
        "duplicate",
        "reorder",
        "port",
        "declared",
        "canonical",
        "resolution",
        "ordinal",
    ),
)
def test_independent_meaning_correspondence_rejects_grafts(
    roots, damage: str, monkeypatch
):
    checked, bundle, _, _ = roots["postgres"]
    entry = bundle.entries[0]
    if damage == "root":
        bad = replace(bundle, verification=roots["mysql"][0])
    elif damage == "tail":
        bad = replace(bundle, entries=bundle.entries[:-1])
    elif damage == "duplicate":
        bad = replace(bundle, entries=(entry,) * 4)
    elif damage == "reorder":
        bad = replace(bundle, entries=bundle.entries[::-1])
    else:
        key = {"port": "source_port"}.get(damage, damage)
        value = True if damage == "ordinal" else copy(getattr(entry, key))
        bad = replace(
            bundle, entries=(replace(entry, **{key: value}), *bundle.entries[1:])
        )

    def forbidden(*args, **kwargs):
        raise AssertionError("verifier reacquired meaning")

    monkeypatch.setattr(meaning, "acquire_scalar_meaning", forbidden)
    with pytest.raises(meaning.ScalarMeaningError):
        meaning.verify_scalar_meaning(bad, checked)
    result = emit_project_sql(
        checked, probe.temporal_input("postgres"), scalar_meaning=bad
    )
    assert result.status == "INPUT_REJECTED" and result.artifact is None


@pytest.mark.parametrize(
    "position,updates",
    (
        (0, {"calendar": "julian"}),
        (0, {"resolution": "millisecond"}),
        (0, {"timezone": "UTC"}),
        (0, {"lower": (1, 1, 1, 0, 0, 0, 0)}),
        (0, {"upper": (9999, 12, 31, 23, 59, 59, 999999)}),
        (0, {"lower": (True, 1, 1, 0, 0, 0, 0)}),
        (2, {"byte_order": "little_endian"}),
        (2, {"byte_width": True}),
    ),
)
def test_meaning_law_is_closed_before_emission(roots, position, updates):
    checked, bundle, _, _ = roots["postgres"]
    entries = list(bundle.entries)
    entries[position] = replace(
        entries[position], law=replace(entries[position].law, **updates)
    )
    bad = replace(bundle, entries=tuple(entries))
    with pytest.raises(meaning.ScalarMeaningError, match="MEANING_LAW"):
        meaning.verify_scalar_meaning(bad, checked)
    assert (
        emit_project_sql(
            checked, probe.temporal_input("postgres"), scalar_meaning=bad
        ).status
        == "INPUT_REJECTED"
    )


def test_meaning_corruption_invalidates_already_built_artifact(roots):
    checked, bundle, artifact, neutral = roots["postgres"]
    before = bundle.entries
    try:
        object.__setattr__(bundle, "entries", before[:-1])
        assert not verify_project_sql_emission(artifact, artifact.request).verified
        with pytest.raises(contract.ResultError, match="MEANING_FIELDS"):
            contract.verify_result_contract(neutral, checked)
    finally:
        object.__setattr__(bundle, "entries", before)
    assert verify_project_sql_emission(artifact, artifact.request).verified


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "position,change",
    ((0, "precision"), (0, "storage"), (2, "encoding"), (2, "storage")),
)
def test_meaning_cannot_repair_physical_declaration(roots, target, position, change):
    checked, bundle, _, _ = roots[target]
    doc = json.loads(probe.temporal_input(target))
    rep = doc["sources"][0]["fields"][position]["representation"]
    if change == "precision":
        rep["storage"]["fractional_seconds"] = 3
    elif change == "encoding":
        rep["domain"]["encoding"] = "mixed_endian"
    else:
        rep["storage"] = {"kind": "pg_int8" if target == "postgres" else "my_bigint"}
    result = emit_project_sql(checked, json.dumps(doc).encode(), scalar_meaning=bundle)
    assert (
        result.status
        == ("INPUT_REJECTED" if change in ("encoding", "precision") else "BLOCKED")
        and result.artifact is None
    )


@pytest.fixture(scope="module")
def products(tmp_path_factory):
    root = tmp_path_factory.mktemp("temporal-products")
    return {
        target: probe.temporal_fixture(root / target, target, mixed=True)
        for target in ("postgres", "mysql")
    }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_checked_producer_exact_ticks_bytes_and_all_old_scalar_requests(
    products, target
):
    from pietto._project import project_arrow_result as arrow

    checked, bundle, artifact, neutral, producer = products[target]
    assert producer.contract.scalar_meaning is artifact.request.scalar_meaning is bundle
    rows = probe.temporal_rows(target, mixed=True)
    for i, row in enumerate(rows):
        assert arrow._value(row[0], producer.fields[0]) == probe.TIME_TICKS[i]
        assert arrow._value(row[2], producer.fields[2]) == bytes.fromhex(
            probe.UUID_HEX[i]
        )
    assert arrow._uuid_representations(producer, None) == (
        None,
        None,
        "uuid",
        "uuid",
        None,
        None,
        None,
        None,
        None,
    )
    requests = tuple(
        arrow.UUIDRepresentationRequest(f.field, "binary16") if i in (2, 3) else None
        for i, f in enumerate(producer.fields)
    )
    assert arrow._uuid_representations(producer, requests) == (
        None,
        None,
        "binary16",
        "binary16",
        None,
        None,
        None,
        None,
        None,
    )
    with pytest.raises(contract.ResultError, match="ARROW_DEPENDENCY_MISSING"):
        arrow.bind_arrow(producer, uuid_representations=requests)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_temporal_carrier_and_precise_endpoint_policy(products, target):
    from datetime import datetime, date, timezone
    from uuid import UUID
    from pietto._project import project_arrow_result as arrow

    producer = products[target][4]

    class DatetimeSubclass(datetime):
        pass

    for value in (
        date(1970, 1, 1),
        DatetimeSubclass(1970, 1, 1),
        datetime(1970, 1, 1, tzinfo=timezone.utc),
        datetime(1970, 1, 1, fold=1),
        datetime(999, 12, 31, 23, 59, 59, 999999),
        datetime(9999, 12, 31, 23, 59, 59, 500000),
        0,
        0.0,
        "1970-01-01",
        probe.CoercibleScalar(),
    ):
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._value(value, producer.fields[0])
    assert (
        arrow._value(datetime(9999, 12, 31, 23, 59, 58, 999999), producer.fields[0])
        == 253402300798999999
    )

    class UUIDSubclass(UUID):
        pass

    class BytesSubclass(bytes):
        pass

    identifier = UUID("00112233-4455-6677-8899-aabbccddeeff")
    invalid = (
        (identifier.bytes, UUIDSubclass(int=1))
        if target == "postgres"
        else (identifier, BytesSubclass(identifier.bytes))
    )
    for value in (
        *invalid,
        b"",
        b"x" * 15,
        b"x" * 17,
        bytearray(identifier.bytes),
        memoryview(identifier.bytes),
        str(identifier),
        1,
        True,
        probe.CoercibleScalar(),
    ):
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._value(value, producer.fields[2])


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_observed_meaning_and_storage_lies_precede_arrow(products, target):
    from pietto._project import project_result_binding as binding
    from pietto._project import project_arrow_result as arrow

    _, bundle, artifact, neutral, producer = products[target]
    observations = probe.temporal_observations(target, mixed=True)
    for position, change in (
        (0, {"fractional_seconds": 3}),
        (0, {"fractional_seconds": 6.0}),
        (0, {"carrier": "int"}),
        (0, {"meaning": replace(meaning.TimestampMeaning(), timezone="UTC")}),
        (2, {"meaning": replace(meaning.UUIDMeaning(), byte_order="little_endian")}),
        (2, {"meaning": replace(meaning.UUIDMeaning(), byte_width=16.0)}),
        (2, {"carrier": "str"}),
        (2, {"lower": 0}),
        (4, {"meaning": meaning.UUIDMeaning()}),
    ):
        values = list(observations)
        values[position] = replace(values[position], **change)
        with pytest.raises(contract.ResultError, match="PRODUCER_OBSERVATION"):
            binding.bind_producer(neutral, artifact, tuple(values))
    no_meaning = contract.build_result_contract(neutral.authority)
    with pytest.raises(contract.ResultError, match="PRODUCER_ROOT"):
        binding.bind_producer(no_meaning, artifact, observations)
    bad = replace(
        producer,
        fields=(
            replace(
                producer.fields[0],
                observation=replace(observations[0], fractional_seconds=3),
            ),
            *producer.fields[1:],
        ),
    )
    with pytest.raises(contract.ResultError, match="PRODUCER_OBSERVATION"):
        arrow.bind_arrow(bad)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_conditional_meaning_codec_and_independent_live_correspondence(
    products, target, monkeypatch
):
    from pietto._project import project_result_contract_portable as writer
    from pietto._project import project_result_contract_pure_boundary as pure
    from pietto._project import project_result_contract_correspondence as runtime

    checked, bundle, _, neutral, _ = products[target]
    exported = writer.export_result_contract(neutral, checked)
    runtime.verify_bound_export(exported, checked)
    document = exported.view.document
    assert len(document["scalar_meaning"]["sources"]) == 4
    assert [f.get("meaning") for f in document["fields"]] == [
        0,
        1,
        2,
        3,
        None,
        None,
        None,
        None,
        None,
    ]

    def forbidden(*args, **kwargs):
        raise AssertionError("checker rebuilt meaning/export")

    monkeypatch.setattr(meaning, "acquire_scalar_meaning", forbidden)
    monkeypatch.setattr(writer, "export_result_contract", forbidden)
    runtime.verify_bound_export(exported, checked)
    bad = json.loads(exported.canonical_bytes)
    bad["fields"][0].pop("meaning")
    with pytest.raises(pure.ContractDocumentError):
        pure.decode_contract(pure.encode_document(bad))
    bad = json.loads(exported.canonical_bytes)
    bad["scalar_meaning"]["sources"][0]["law"]["upper"][-1] = 999999
    with pytest.raises(pure.ContractDocumentError):
        pure.decode_contract(pure.encode_document(bad))
    bad = json.loads(exported.canonical_bytes)
    sources = bad["scalar_meaning"]["sources"]
    sources[2]["port"], sources[3]["port"] = sources[3]["port"], sources[2]["port"]
    view = pure.decode_contract(pure.encode_document(bad))
    with pytest.raises(contract.ResultError, match="CORRESPONDENCE"):
        runtime.verify_contract_correspondence(view, neutral, checked)
    bad = json.loads(exported.canonical_bytes)
    bad.pop("scalar_meaning")
    for field in bad["fields"]:
        field.pop("meaning", None)
    view = pure.decode_contract(pure.encode_document(bad))
    with pytest.raises(contract.ResultError, match="CORRESPONDENCE"):
        runtime.verify_contract_correspondence(view, neutral, checked)


@pytest.mark.parametrize("declaration", ("Stamp", 'Timestamp(tz = "UTC")'))
def test_nominal_or_uninterpreted_arguments_do_not_create_temporal_meaning(
    tmp_path, declaration
):
    text = probe.temporal_source("postgres").replace(
        "stamp: Timestamp", "stamp: " + declaration
    )
    if declaration == "Stamp":
        text = "type Stamp = Timestamp\n" + text
    checked = probe.build_neutral(tmp_path / "source", {"main.pietto": text})
    with pytest.raises(meaning.ScalarMeaningError, match="MEANING_FIELDS"):
        meaning.acquire_scalar_meaning(checked)


@pytest.mark.parametrize("slot", ("request", "field"))
def test_deleted_meaning_reference_is_a_typed_realization_failure(roots, slot):
    from pietto._project.project_sql_emission import realize_project_sql

    _, _, artifact, _ = roots["postgres"]
    selected = (
        artifact.request if slot == "request" else artifact.request.sources[0].fields[0]
    )
    before = selected.scalar_meaning
    try:
        object.__delattr__(selected, "scalar_meaning")
        result = realize_project_sql(artifact.request)
        assert result.status == "BLOCKED" and [
            (b.code, b.detail) for b in result.blockers
        ] == [("PIE-B1008", "scalar_meaning_correspondence")]
        assert not verify_project_sql_emission(artifact, artifact.request).verified
    finally:
        object.__setattr__(selected, "scalar_meaning", before)
    assert verify_project_sql_emission(artifact, artifact.request).verified


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_explicit_meaning_does_not_open_other_lowerings(tmp_path, target):
    source = probe.temporal_source(target, mixed=True).replace(
        "    select:\n", "    where number > 0\n    select:\n"
    )
    checked = probe.build_neutral(tmp_path / "filter", {"main.pietto": source})
    bundle = meaning.acquire_scalar_meaning(checked)
    result = emit_project_sql(
        checked, probe.temporal_input(target, mixed=True), scalar_meaning=bundle
    )
    assert result.status == "BLOCKED" and [
        (b.code, b.detail) for b in result.blockers
    ] == [("PIE-B1003", "scalar_meaning_requires_field_projection")]
