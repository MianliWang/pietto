"""Actual source meaning acquisition precedes private physical result adaptation."""

from dataclasses import replace
from copy import copy
from datetime import datetime
import importlib.util
import json
from uuid import UUID

import pytest

import _pietto_results_product as probe
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
def test_actual_builtin_meaning_is_automatically_derived(roots, target):
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
    automatic = emit_project_sql(checked, probe.temporal_input(target))
    assert automatic.status == "VERIFIED" and automatic.artifact is not None
    assert automatic.artifact.request.scalar_meaning is not None
    assert [
        e.canonical.name for e in automatic.artifact.request.scalar_meaning.entries
    ] == ["Timestamp", "Timestamp", "UUID", "UUID"]
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
    import _pietto_results_correspondence as runtime

    checked, bundle, _, neutral, _ = products[target]
    exported = writer.export_result_contract(neutral, checked)
    runtime.verify_bound_export(exported, checked)
    document = exported.view.document
    assert len(document["scalar_meaning"]["sources"]) == 4
    assert "statement_clock" not in document
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
def test_intrinsic_meaning_admits_temporal_equality_grouping_and_uuid_order(
    tmp_path, target
):
    """Q3: a UUID result ORDER key keeps its source meaning; both targets
    order it by its unsigned big-endian bytes."""
    prefix = f"""shape Row:
    stamp: Timestamp
    identifier: UUID
source rows: Row = {target}.table("opaque.result.fixture")
query result:
    from rows
"""
    source = {
        "equality": prefix
        + "    where stamp == stamp and identifier == identifier\n"
        + "    select:\n        s = stamp\n        u = identifier\n",
        "grouping": prefix
        + "    group by:\n        stamp\n        identifier\n"
        + "    select:\n        s = stamp\n        u = identifier\n        total = count()\n",
        "order": prefix
        + "    select:\n        s = stamp\n        u = identifier\n"
        + "    order by:\n        stamp\n",
        "uuid_order": prefix
        + "    select:\n        s = stamp\n        u = identifier\n"
        + "    order by:\n        identifier\n",
    }
    document = json.loads(probe.temporal_input(target))
    document["sources"][0]["fields"] = [
        document["sources"][0]["fields"][0],
        {**document["sources"][0]["fields"][2], "ordinal": 1},
    ]
    document["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    encoded = json.dumps(document).encode()
    q = '"' if target == "postgres" else "`"
    for name in source:
        checked = probe.build_neutral(tmp_path / name, {"main.pietto": source[name]})
        result = emit_project_sql(checked, encoded)
        assert result.status == "VERIFIED" and result.artifact is not None
        assert result.artifact.request.scalar_meaning is not None
        if name == "uuid_order":
            assert result.artifact.rendered.sql.endswith(
                f" ORDER BY {q}t0{q}.{q}c2{q} ASC".encode()
            )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_min_of_a_timestamp_keeps_its_source_meaning(tmp_path, target):
    """A `min(stamp)` result traces to its Timestamp source through its
    aggregate edge, so the result contract carries Timestamp meaning."""
    source = f"""shape Row:
    stamp: Timestamp
    identifier: UUID
source rows: Row = {target}.table("opaque.result.fixture")
query result:
    from rows
    group by:
        identifier
    select:
        u = identifier
        first = min(stamp)
"""
    document = json.loads(probe.temporal_input(target))
    document["sources"][0]["fields"] = [
        document["sources"][0]["fields"][0],
        {**document["sources"][0]["fields"][2], "ordinal": 1},
    ]
    document["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    checked = probe.build_neutral(tmp_path / "min", {"main.pietto": source})
    result = emit_project_sql(checked, json.dumps(document).encode())
    assert result.status == "VERIFIED" and result.artifact is not None
    scalar = result.artifact.request.scalar_meaning
    assert scalar is not None
    built = contract.build_result_contract(checked, scalar_meaning=scalar)
    assert [
        None if field.meaning is None else field.meaning.canonical.name
        for field in built.shape.fields
    ] == ["UUID", "Timestamp"]
    # A compiled replay traces the same aggregate edge of its own records.
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_result_output import prepare_output

    compiled = build_compiled(result.artifact)
    loaded = load_compiled(
        compiled.payload,
        expected_pin=compiled.pin,
        accepted_producer=compiled.producer,
        accepted_compatibility=compiled.compatibility,
    )
    replayed = prepare_output(emit_compiled(loaded, ()))
    assert [
        None if field.meaning is None else field.meaning.canonical.name
        for field in replayed.contract.shape.fields
    ] == ["UUID", "Timestamp"]


NOW_ACCESS = ("127.0.0.1", 9, "app", "reader", "pw")
TIMESTAMP_LAW = {
    "kind": "timestamp",
    "calendar": "proleptic_gregorian",
    "resolution": "microsecond",
    "timezone": "absent",
    "lower": [1000, 1, 1, 0, 0, 0, 0],
    "upper": [9999, 12, 31, 23, 59, 59, 499999],
}


def _program(directory, body, *, temporal=False):
    """The documented example, `temporal` with its Timestamp source fields,
    followed by `body`."""
    import _pietto_execution_api as api

    writer = api.write_temporal_example if temporal else api.write_example
    project = writer(directory)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + body, encoding="utf-8")
    return project


def _collected(directory, item, *, temporal=False):
    """The relation `members` that `result` collects, with one more item,
    `temporal` with its Timestamp source field `stamp`."""
    import _pietto_execution_api as api

    project = api.write_nested_collect(directory, temporal=temporal)
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8").replace(
            "            t\n", f"            t\n            {item}\n"
        ),
        encoding="utf-8",
    )
    return project


def _compiled(project, kind, name, *, loaded=False):
    import pietto.execution as execution

    query = execution.compile_query(
        project,
        module="main.pietto",
        kind=kind,
        name=name,
        dialect="postgres",
        emission_contract="contract.json",
    )
    if not loaded:
        return query
    bundle = execution.export_bundle(query)
    return execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )


def _executed(query, schemas=("fixture", "pg_catalog"), parameters=None):
    """The result contract of an unopened execute() attempt; nothing connects."""
    import pietto.execution as execution

    handle = execution.execute(
        query,
        route="postgres_rows",
        access=execution.PostgresAccess(*NOW_ACCESS),
        premise=execution.PostgresDeploymentPremise(schemas),
        parameters=parameters,
    )
    try:
        return handle._owner.request.contract
    finally:
        handle.close()


@pytest.mark.parametrize("loaded", (False, True), ids=("live", "loaded"))
def test_now_outputs_carry_the_statement_clock_meaning(tmp_path, loaded):
    """Without a Timestamp or UUID source there is no meaning bundle, yet a
    value that is a whole `now()` call carries the statement clock through the
    compiled authority of execute(): two reads, a `def` argument, an upstream
    relation's column, its `max`, which admits NULL, and a collected child.
    The contract alone refuses no other Timestamp: that is the guard's."""
    from pietto._project.project_sql_plan_verification import (
        CompiledSQLPlanVerification,
    )

    project = _program(
        tmp_path / "flat",
        "def same(x: Timestamp) -> Timestamp:\n    return x\n"
        "table twice:\n    from items\n    select:\n"
        "        id\n        seen = now()\n        again = now()\n"
        "table passed:\n    from items\n    select:\n"
        "        id\n        seen = same(now())\n"
        "table upstream:\n    from twice\n    select:\n        id\n        seen\n"
        "table latest:\n    from twice\n    group by:\n        id\n"
        "    select:\n        id\n        last = max(seen)\n"
        "table computed:\n    from items\n    select:\n"
        "        id\n        seen = now()\n        c = coalesce(now(), now())\n",
    )
    clock = meaning.STATEMENT_CLOCK
    for name, nullability in (
        ("twice", ["non_null", "non_null"]),
        ("passed", ["non_null"]),
        ("upstream", ["non_null"]),
        ("latest", ["nullable"]),
    ):
        built = _executed(_compiled(project, "table", name, loaded=loaded))
        assert type(built.authority) is CompiledSQLPlanVerification
        assert built.scalar_meaning is None
        leaves = built.shape.fields[1:]
        assert all(leaf.meaning is clock for leaf in leaves)
        assert [leaf.nullability.value for leaf in leaves] == nullability
    request = _compiled(project, "table", "computed", loaded=loaded)._template
    built = contract.build_result_contract(request.artifact.request.verification)
    assert type(built.authority) is CompiledSQLPlanVerification
    assert [f.meaning for f in built.shape.fields[1:]] == [clock, None]
    nested = _collected(tmp_path / "nested", "seen = now()")
    built = _executed(
        _compiled(nested, "query", "result", loaded=loaded), ("public", "pg_catalog")
    )
    (collection,) = (
        f for f in built.shape.fields if type(f.shape) is contract.NestedShape
    )
    child = collection.shape.fields[-1]
    assert (child.label, child.meaning, child.nullability.value) == (
        "seen",
        clock,
        "non_null",
    )


@pytest.mark.parametrize("loaded", (False, True), ids=("live", "loaded"))
def test_now_output_beside_a_source_timestamp_runs_with_its_own_meaning(
    tmp_path, loaded
):
    """Beside Timestamp source fields, `now()` keeps the statement clock and
    `stamp` its source entry, also in a collected child; an expression over
    `now()` has no meaning, and a collected one is refused by the child."""
    import pietto.execution as execution

    project = _program(
        tmp_path,
        "table snap:\n    from items\n    select:\n"
        "        id\n        stamp\n        seen = now()\n"
        "table mixed:\n    from items\n    select:\n"
        "        id\n        c = coalesce(opt, now())\n",
        temporal=True,
    )
    built = _executed(_compiled(project, "table", "snap", loaded=loaded))
    entries = built.scalar_meaning.entries
    assert [e.canonical.name for e in entries] == ["Timestamp", "Timestamp"]
    leaves = built.shape.fields
    assert leaves[0].meaning is None and leaves[1].meaning is entries[0]
    assert leaves[2].meaning is meaning.STATEMENT_CLOCK
    assert [leaf.nullability.value for leaf in leaves] == ["non_null"] * 3
    with pytest.raises(execution.RequestRejected) as refused:
        _executed(_compiled(project, "table", "mixed", loaded=loaded))
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "MEANING_OUTPUT",
    )
    schemas = ("public", "pg_catalog")
    nested = _collected(tmp_path / "seen", "seen = now()", temporal=True)
    built = _executed(_compiled(nested, "query", "result", loaded=loaded), schemas)
    (collection,) = (
        f for f in built.shape.fields if type(f.shape) is contract.NestedShape
    )
    children = {child.label: child for child in collection.shape.fields}
    assert children["stamp"].meaning is built.scalar_meaning.entries[0]
    assert children["seen"].meaning is meaning.STATEMENT_CLOCK
    assert children["seen"].nullability.value == "non_null"
    nested = _collected(tmp_path / "c", "c = coalesce(now(), now())", temporal=True)
    with pytest.raises(execution.RequestRejected) as refused:
        _executed(_compiled(nested, "query", "result", loaded=loaded), schemas)
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "MEANING_UNAVAILABLE",
    )


def test_plan_authority_without_source_meaning_carries_the_clock(tmp_path):
    """The plan authority traces the same edges without a meaning bundle:
    only the whole `now()` call is the clock, also in a collected child, and
    the portable document then describes the clock without any scalar
    meaning."""
    from pietto._project import project_result_contract_portable as writer
    import _pietto_results_correspondence as runtime

    checked = probe.build_neutral(
        tmp_path / "plain",
        {
            "main.pietto": "shape Row:\n    id: Int\n"
            'source rows: Row = postgres.table("opaque.result.fixture")\n'
            "table result:\n    from rows\n    select:\n"
            "        id\n        seen = now()\n        c = coalesce(now(), now())\n"
        },
    )
    built = contract.build_result_contract(checked)
    assert [f.meaning for f in built.shape.fields] == [
        None,
        meaning.STATEMENT_CLOCK,
        None,
    ]
    exported = writer.export_result_contract(built, checked)
    document = exported.view.document
    assert "scalar_meaning" not in document
    assert document["statement_clock"] == TIMESTAMP_LAW
    assert [f.get("meaning") for f in document["fields"]] == [
        None,
        "statement_clock",
        None,
    ]
    runtime.verify_bound_export(exported, checked)
    checked = probe.build_neutral(
        tmp_path / "nested",
        {
            "main.pietto": "shape Kid:\n    parent: Int\n    seq: Int\n"
            "shape Row:\n    id: Int\n"
            'source rows: Row = postgres.table("opaque.result.fixture")\n'
            'source kids: Kid = postgres.table("opaque.result.kids")\n'
            "query result:\n    let members:\n        capture rows\n"
            "        from kids\n        where kids.parent == rows.id\n"
            "        select:\n            seq\n            seen = now()\n"
            "        order by:\n            seq\n"
            "    from rows\n    select:\n        id\n        c = collect members\n"
        },
    )
    built = contract.build_result_contract(checked)
    collected = built.shape.fields[1].shape
    assert isinstance(collected, contract.NestedShape)
    assert collected.fields[1].meaning is meaning.STATEMENT_CLOCK
    exported = writer.export_result_contract(built, checked)
    document = exported.view.document
    assert document["statement_clock"] == TIMESTAMP_LAW
    children = document["fields"][1]["element"]["fields"]
    assert [f.get("meaning") for f in children] == [None, "statement_clock"]
    runtime.verify_bound_export(exported, checked)


@pytest.fixture(scope="module")
def clocked(tmp_path_factory):
    """The temporal premise's four source outputs, then `seen` and `again`."""
    source = probe.temporal_source("postgres") + (
        "        seen = now()\n        again = now()\n"
    )
    checked = probe.build_neutral(
        tmp_path_factory.mktemp("clocked") / "project", {"main.pietto": source}
    )
    bundle = meaning.acquire_scalar_meaning(checked)
    return (
        checked,
        bundle,
        contract.build_result_contract(checked, scalar_meaning=bundle),
    )


def test_now_and_source_outputs_keep_their_own_meanings(clocked):
    from pietto._project import project_result_contract_portable as writer
    import _pietto_results_correspondence as runtime

    checked, bundle, built = clocked
    clock = meaning.STATEMENT_CLOCK
    assert [f.meaning for f in built.shape.fields] == [*bundle.entries, clock, clock]
    exported = writer.export_result_contract(built, checked)
    runtime.verify_bound_export(exported, checked)
    document = exported.view.document
    assert len(document["scalar_meaning"]["sources"]) == 4
    assert document["statement_clock"] == TIMESTAMP_LAW
    assert [f["meaning"] for f in document["fields"]] == [
        0,
        1,
        2,
        3,
        "statement_clock",
        "statement_clock",
    ]


def _view(document):
    from pietto._project import project_result_contract_pure_boundary as pure

    return pure.decode_contract(pure.encode_document(document))


@pytest.mark.parametrize(
    "damage",
    ("no-clock", "dangling-clock", "uuid-clock", "clock-law"),
)
def test_the_clock_description_is_closed(clocked, damage):
    from pietto._project import project_result_contract_portable as writer
    from pietto._project import project_result_contract_pure_boundary as pure

    checked, _, built = clocked
    bad = json.loads(writer.export_result_contract(built, checked).canonical_bytes)
    if damage == "no-clock":
        bad.pop("statement_clock")
    elif damage == "dangling-clock":
        bad["fields"][4]["meaning"] = bad["fields"][5]["meaning"] = 0
    elif damage == "uuid-clock":
        bad["fields"][2]["meaning"] = "statement_clock"
    else:
        bad["statement_clock"]["upper"][-1] = 999999
    with pytest.raises(pure.ContractDocumentError):
        _view(bad)


@pytest.mark.parametrize(
    "damage", ("clock-to-source", "source-to-clock", "dangling-clock", "clock-law")
)
def test_clock_correspondence_reads_the_verified_leaves(
    roots, clocked, monkeypatch, damage
):
    """A well-formed document that names the other meaning of a leaf does not
    correspond; neither does a clock description that the wire check missed,
    which the verified leaves do not read or whose law differs."""
    from pietto._project import project_result_contract_portable as writer
    from pietto._project import project_result_contract_pure_boundary as pure
    import _pietto_results_correspondence as runtime

    checked, _, built = clocked
    if damage == "dangling-clock":
        checked, _, _, built = roots["postgres"]
    bad = json.loads(writer.export_result_contract(built, checked).canonical_bytes)
    if damage == "clock-to-source":
        bad["fields"][4]["meaning"] = 0
    elif damage == "source-to-clock":
        bad["fields"][0]["meaning"] = "statement_clock"
    else:
        monkeypatch.setattr(pure, "validate_document", lambda doc, **_: doc)
        bad["statement_clock"] = json.loads(json.dumps(TIMESTAMP_LAW))
        if damage == "clock-law":
            bad["statement_clock"]["upper"][-1] = 999999
    with pytest.raises(contract.ResultError, match="CORRESPONDENCE"):
        runtime.verify_contract_correspondence(_view(bad), built, checked)


@pytest.mark.parametrize("position,graft", ((4, "source"), (0, "clock")))
def test_clock_and_source_meanings_are_not_grafted(clocked, position, graft):
    checked, bundle, built = clocked
    fields = list(built.shape.fields)
    fields[position] = replace(
        fields[position],
        meaning=bundle.entries[0] if graft == "source" else meaning.STATEMENT_CLOCK,
    )
    bad = replace(built, shape=contract.ResultShape(tuple(fields)))
    with pytest.raises(contract.ResultError, match="FIELD"):
        contract.verify_result_contract(bad, checked)


@pytest.mark.parametrize(
    ("found", "complete", "kind", "strict", "expected"),
    (
        ("source-and-clock", True, "Timestamp", True, "MEANING_OUTPUT"),
        ("clock", True, "UUID", True, "MEANING_OUTPUT"),
        ("clock", True, "Timestamp", True, "clock"),
        ("clock-twice", True, "Timestamp", True, "clock"),
        ("none", True, "Timestamp", True, "MEANING_OUTPUT"),
        ("clock", False, "Timestamp", True, "MEANING_OUTPUT"),
        ("source", True, "Timestamp", True, "source"),
        ("clock", False, "Timestamp", False, None),
        ("none", True, "Timestamp", False, None),
        ("clock", True, "UUID", False, None),
        ("source", True, "Timestamp", False, None),
        ("source-and-clock", True, "Timestamp", False, None),
        ("clock", True, "Timestamp", False, "clock"),
        ("clock-twice", True, "Timestamp", False, "clock"),
    ),
)
def test_a_traced_output_resolves_to_one_meaning(
    roots, found, complete, kind, strict, expected
):
    """Mixed ends, a UUID port at the clock, a cycle (nothing found) and an
    incomplete trace are closed; the language cannot reach most of them. Two
    reads of the clock are one end."""
    source = roots["postgres"][1].entries[0]
    ends = {
        "source-and-clock": [source, meaning.STATEMENT_CLOCK],
        "clock": [meaning.STATEMENT_CLOCK],
        "clock-twice": [meaning.STATEMENT_CLOCK, meaning.STATEMENT_CLOCK],
        "source": [source],
        "none": [],
    }[found]
    if expected == "MEANING_OUTPUT":
        with pytest.raises(meaning.ScalarMeaningError, match="MEANING_OUTPUT"):
            meaning._resolved(ends, complete, kind, strict)
        return
    resolved = meaning._resolved(ends, complete, kind, strict)
    assert (
        resolved
        is {
            None: None,
            "clock": meaning.STATEMENT_CLOCK,
            "source": source,
        }[expected]
    )


@pytest.mark.parametrize(
    ("program", "kind", "item", "parameters"),
    (
        (
            "query snap(start: Timestamp):",
            "query",
            "since = start",
            {"start": datetime(2026, 1, 2)},
        ),
        ("query snap(key: UUID):", "query", "who = key", {"key": UUID(int=1)}),
        ("table snap:", "table", "c = coalesce(now(), now())", None),
        (None, "query", "c = coalesce(now(), now())", None),
    ),
    ids=("timestamp-parameter", "uuid-parameter", "computed-now", "collected"),
)
def test_a_timestamp_output_without_source_meaning_is_refused_before_it_runs(
    tmp_path, monkeypatch, program, kind, item, parameters
):
    """Without a Timestamp or UUID source the program has no scalar meaning, so
    a Timestamp or UUID parameter, or an expression over `now()`, selected as an
    output, also in a collected child relation, is refused while execute() and
    save() prepare the result, as it is beside such a source, before any
    connection, workspace or schema export."""
    import pietto.execution as execution
    from pietto._project import project_job_workspace as private_workspace

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused save opened workspace state")

    monkeypatch.setattr(private_workspace, "open_workspace", forbidden)
    if program is None:
        project = _collected(tmp_path, item)
        name, schemas = "result", ("public", "pg_catalog")
    else:
        project = _program(
            tmp_path,
            f"{program}\n    from items\n    select:\n        id\n        {item}\n",
        )
        name, schemas = "snap", ("fixture", "pg_catalog")
    query = _compiled(project, kind, name)
    with pytest.raises(execution.RequestRejected) as refused:
        _executed(query, schemas, parameters)
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "0" * 32)
    with pytest.raises(execution.RequestRejected) as saved:
        execution.save(
            workspace,
            query,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=execution.PostgresAccess(*NOW_ACCESS),
            premise=execution.PostgresDeploymentPremise(schemas),
            parameters=parameters,
        )
    for error in (refused.value, saved.value):
        assert (error.code, error.detail) == ("PIE-R1004", "MEANING_OUTPUT")
