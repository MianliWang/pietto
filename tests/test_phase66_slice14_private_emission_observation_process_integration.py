"""Phase66 Slice14 private emission observation and its real process family."""

from __future__ import annotations

import base64
import dataclasses
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import sys
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as emission
from pietto._project import project_sql_emission_portable as portable
from pietto._project import project_sql_emission_portable_schema as schema
from pietto._project import project_sql_emission_pure_boundary as pure

SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))
OK = pure.Status.OK
_BUILT: dict[tuple[str, str, str], Any] = {}


def _outcome(tmp_path_factory, target, case, variant):
    key = (target, case, variant)
    if key not in _BUILT:
        item = emission.fixture(target, case, variant)
        root = tmp_path_factory.mktemp("slice14-" + case.lower())
        _BUILT[key] = emission.build_case(
            root, item["source"], item["contract"], item["policy"]
        )[1]
    return _BUILT[key]


def _observed(tmp_path_factory, target, case, variant):
    artifact = _outcome(tmp_path_factory, target, case, variant).artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    return artifact, observed.canonical_bytes


def _encode(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _walk(spec: str, value: Any, visit) -> Any:
    if value is None:
        return None
    if spec.startswith("?"):
        return _walk(spec[1:], value, visit)
    if spec.startswith("*"):
        return [_walk(spec[1:], item, visit) for item in value]
    if spec.startswith("@") or (spec == "subject" and type(value) is list):
        return visit(value)
    if spec == "scope" and value != "statement":
        if type(value[0]) is list:
            return [visit(value[0]), value[1]]
        return visit(value)
    return value


def _recanonical(document: dict[str, Any]) -> dict[str, Any]:
    """Test-side reindexing after a structural edit (drops unreachable records)."""
    fields = {tuple(r["ref"]): r["fields"] for r in document["records"]}
    order: list[tuple[str, int]] = []
    mapping: dict[tuple[str, int], tuple[str, int]] = {}
    counters: dict[str, int] = {}
    stack = [("artifact", 0)]
    while stack:
        ref = stack.pop()
        if ref in mapping:
            continue
        mapping[ref] = (ref[0], counters.get(ref[0], 0))
        counters[ref[0]] = mapping[ref][1] + 1
        order.append(ref)
        children: list[tuple[str, int]] = []
        for name, spec in schema.RECORDS[ref[0]]:
            _walk(spec, fields[ref][name], lambda r: children.append(tuple(r)) or r)
        stack.extend(reversed(children))
    records = [
        {
            "ref": list(mapping[ref]),
            "fields": {
                name: _walk(spec, fields[ref][name], lambda r: list(mapping[tuple(r)]))
                for name, spec in schema.RECORDS[ref[0]]
            },
        }
        for ref in order
    ]
    return {**document, "records": records}


def _records(document, kind):
    return [r["fields"] for r in document["records"] if r["ref"][0] == kind]


def _record(document, ref):
    for row in document["records"]:
        if row["ref"] == list(ref):
            return row["fields"]
    raise KeyError(ref)


def _status(data: bytes) -> tuple[pure.Status, str | None]:
    outcome = pure.parse_emission_observation(data)
    if outcome.status is not OK:
        assert outcome.view is None and outcome.canonical_bytes is None
    return outcome.status, outcome.detail


def _events(document):
    rendered = _records(document, "rendered")[0]
    return [_record(document, ref) for ref in rendered["events"]]


# -- closed schema, shared constants and the data-only import boundary ------


def test_schema_mirrors_emission_runtime_classes_and_shared_constants():
    from pietto._project import project_sql_emission_contract as contract
    from pietto._project import project_sql_emission_joins as joining
    from pietto._project import project_sql_emission_parameters as parameters
    from pietto._project import project_sql_emission_results as resulting
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project import project_sql_emission_sets as setting
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project.project_sql_plan import ProjectSQLPlanRefKind

    assert set(portable.KINDS.values()) | {portable.PAIR_KIND} == set(schema.RECORDS)
    upstream = {"owner", "fixed_value", "origin", "association"}
    for cls, kind in portable.KINDS.items():
        names = {name for name, _ in schema.RECORDS[kind]}
        derived = schema.DERIVED.get(kind, frozenset())
        assert derived <= names
        if kind in upstream:
            assert all(hasattr(cls, n) or n in derived for n in names), kind
            continue
        own = {field.name for field in dataclasses.fields(cls)}
        assert own <= names | schema.CUTOFF.get(kind, frozenset()), kind
        assert names <= own | derived, kind
        assert not (schema.CUTOFF.get(kind, frozenset()) & names), kind
    assert schema.PLAN_KINDS == {kind.value for kind in ProjectSQLPlanRefKind}
    assert schema.FAMILIES == contract.RELEASES
    assert schema.PHYSICAL == parameters.PHYSICAL
    assert schema.ANCHOR_SUFFIX == {
        physical: parameters.anchor_suffix(physical)
        for physical in parameters.SQL_TYPES
    }
    assert schema.COMPARISON_SPELLING == rows.COMPARISONS
    assert schema.WINDOW_SPELLING == windowing.SPELLING
    assert schema.FRAME_UNITS == windowing.UNIT_SPELLING
    assert schema.FRAME_BOUNDS == windowing.BOUND_SPELLING
    assert schema.FRAME_OFFSETS == windowing.OFFSET_BOUNDS
    assert {
        k.value: (None if v is None else " " + v)
        for k, v in (
            (k, windowing.EXCLUSION_SPELLING.get(k))
            for k in windowing.EXCLUSION_TARGETS
        )
    } == schema.EXCLUSIONS
    assert {k.value: " " + v + " " for k, v in joining.NATIVE_KINDS.items()} == (
        schema.JOIN_SPELLING
    )
    assert set(joining.MEMBERSHIP.values()) == set(schema.MEMBERSHIP_SPELLING)
    assert {
        k.value: v for k, v in setting.KIND_SPELLING.items()
    } == schema.SET_KINDS and {
        k.value: v for k, v in setting.QUANTIFIER_SPELLING.items()
    } == schema.SET_QUANTIFIERS
    assert {k: " " + v for k, v in resulting.DIRECTIONS.items()} == schema.DIRECTIONS
    assert resulting.CARRIERS == schema.CARRIERS
    # The nested association encoders shared by export and correspondence keep
    # every field of their live upstream identity classes.
    from pietto._project import module_attribution as attribution
    from pietto._project.module_bindings import ProjectImportedBindingIdentity
    from pietto._project.module_catalog import ProjectNominalDeclarationIdentity
    from pietto._project.project_sql_plan_source_maps import ProjectSQLSourcePosition

    def field_names(cls):
        return {field.name for field in dataclasses.fields(cls)}

    def namespace(cls, **nested):
        return SimpleNamespace(**{**{n: n for n in field_names(cls)}, **nested})

    nominal = namespace(ProjectNominalDeclarationIdentity)
    occurrence = namespace(
        attribution.ProjectDeclarationOccurrenceIdentity, identity=nominal
    )
    imported = namespace(
        attribution.ProjectModuleImportOccurrenceIdentity,
        binding_identity=namespace(ProjectImportedBindingIdentity),
    )
    facade = namespace(attribution.ProjectModuleFacadeOccurrenceIdentity)
    hop = namespace(
        attribution.ProjectModuleAccessHop,
        import_occurrence=imported,
        facade_occurrence=facade,
        target_identity=nominal,
    )
    path = namespace(
        attribution.ProjectModuleOriginPath,
        target_occurrence=occurrence,
        local_occurrence=occurrence,
        import_occurrence=imported,
        hops=(hop,),
    )
    encoded_path = portable._path(path)
    assert encoded_path is not None
    assert set(encoded_path) == field_names(attribution.ProjectModuleOriginPath)
    assert set(encoded_path["target_occurrence"]) == field_names(
        attribution.ProjectDeclarationOccurrenceIdentity
    )
    assert set(encoded_path["target_occurrence"]["identity"]) == field_names(
        ProjectNominalDeclarationIdentity
    )
    assert set(encoded_path["import_occurrence"]) == field_names(
        attribution.ProjectModuleImportOccurrenceIdentity
    )
    assert set(encoded_path["import_occurrence"]["binding_identity"]) == field_names(
        ProjectImportedBindingIdentity
    )
    (encoded_hop,) = encoded_path["hops"]
    assert set(encoded_hop) == field_names(attribution.ProjectModuleAccessHop)
    assert set(encoded_hop["facade_occurrence"]) == field_names(
        attribution.ProjectModuleFacadeOccurrenceIdentity
    )
    # The original span/location object is the source of line/column; it is the
    # one position field not transported.
    assert set(portable._location(namespace(ProjectSQLSourcePosition))) == (
        field_names(ProjectSQLSourcePosition) - {"original"}
    )
    for family in schema.FAMILIES:
        for tag, value in (
            ("Bool", True),
            ("Int", -(1 << 63)),
            ("Float", -0.0),
            ("Float", 1e300),
            ("Text", "雪e\u0301😀\"'\\\n"),
        ):
            value_type = SimpleNamespace(
                kind=parameters.ValueTypeKind.KNOWN,
                resolved_type=SimpleNamespace(
                    kind=parameters.TypeKind.BUILTIN, name=tag
                ),
                nullability=parameters.EffectiveNullability.NON_NULL,
            )
            leaf = parameters.SQLLiteral(
                SimpleNamespace(value_type=value_type), None, value
            )
            assert schema.literal_token(tag, value, family) == (
                parameters.literal_token(leaf, family)
            )


def test_pure_and_schema_import_closure_is_data_only():
    code = (
        "import sys\n"
        "import pietto._project.project_sql_emission_pure_boundary\n"
        "print('\\n'.join(sorted(m for m in sys.modules if m.split('.')[0] in "
        "('pietto', 'antlr4', 'psycopg', 'mysql'))))\n"
    )
    result = subprocess.run(
        (sys.executable, "-c", code), capture_output=True, text=True, check=True
    )
    assert result.stdout.split() == [
        "pietto",
        "pietto._project",
        "pietto._project.project_sql_emission_portable_schema",
        "pietto._project.project_sql_emission_pure_boundary",
    ]


# -- complete local coverage over every admitted emission --------------------


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_every_admitted_artifact_exports_corresponds_and_decodes(
    tmp_path_factory, target
):
    kinds: set[str] = set()
    failures = []
    statuses = {}
    root = tmp_path_factory.mktemp("slice14-corpus-" + target)
    for number, item in enumerate(emission.generation_inputs(target)):
        case, variant = item["id"], item["variant"]
        # Built and released one at a time; nothing retains the corpus graphs.
        outcome = emission.build_case(
            root / str(number), item["source"], item["contract"], item["policy"]
        )[1]
        statuses[case, variant] = outcome.status
        assert outcome.status == emission.expected_status(case, variant, target)
        artifact = outcome.artifact
        if artifact is None:
            refused = portable.export_emission_observation(outcome, None)
            assert refused == portable.EmissionObservation(
                portable.ObservationStatus.INVALID_ROOT
            )
            continue
        observed = portable.export_emission_observation(artifact, artifact.request)
        if observed.status is not portable.ObservationStatus.OK:
            failures.append((case, variant, "export", observed.status))
            continue
        data = observed.canonical_bytes
        assert data is not None and data.endswith(b"\n") and b"\n" not in data[:-1]
        decoded = pure.parse_emission_observation(data)
        if decoded.status is not OK:
            failures.append((case, variant, decoded.status, decoded.detail))
            continue
        assert decoded.canonical_bytes == data and decoded.view is not None
        again = pure.evaluate_emission_observation(json.loads(data))
        assert again.status is OK and again.canonical_bytes == data
        checked = portable.verify_emission_observation(data, artifact, artifact.request)
        if not checked.corresponds:
            failures.append((case, variant, "correspondence", checked.issues))
        view = decoded.view
        kinds.update(ref.kind for ref in view.order)
        assert view.sql == artifact.rendered.sql
        assert view.at(len(view.sql)) == ()
        assert view.overlapping(3, 3) == ()
        for item_range in (view.ranges[0], view.ranges[-1]):
            assert item_range in view.at(item_range.start)
            assert item_range in view.overlapping(item_range.start, item_range.end)
            assert item_range in view.ranges_of(item_range.subject)
        assert str(tmp_path_factory.getbasetemp()) not in data.decode()
    assert failures == []
    assert (
        sum(status == "VERIFIED" for status in statuses.values())
        == {
            "postgres": 150,
            "mysql": 147,
        }[target]
    )
    # Every record kind the closed schema describes occurs in real output,
    # except the variants no admitted source of this target produces.
    absent = set(schema.RECORDS) - kinds
    assert (
        absent <= {"window_frame", "window_definition"}
        if target == "mysql"
        else (absent == set())
    ), absent


def test_views_are_immutable_and_lookups_follow_slice12_semantics(tmp_path_factory):
    artifact, data = _observed(
        tmp_path_factory, "postgres", "R_fixed_direct", "table_bind"
    )
    view = pure.parse_emission_observation(data).view
    assert view is not None
    with pytest.raises(AttributeError):
        view.sql = b""  # type: ignore[misc]
    record = view.record(pure.Ref("artifact", 0))
    with pytest.raises(TypeError):
        record.fields["request"] = None  # type: ignore[index]
    for bad in (-1, len(view.sql) + 1, True, "0"):
        with pytest.raises(ValueError):
            view.at(bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        view.overlapping(5, 4)
    with pytest.raises(ValueError):
        view.ranges_of(pure.PlanRef("expression", 10**6))
    with pytest.raises(ValueError):
        view.ranges_of(pure.Ref("origin", 10**6))
    parameters = [r for r in view.ranges if r.kind == "parameter"]
    assert parameters
    for token in parameters:
        interior = view.at(token.start)
        assert token in interior and all(
            r.start <= token.start < r.end for r in interior
        )
    origin = next(r for r in view.ranges if r.origins).origins[0]
    assert all(origin in r.origins for r in view.ranges_of(origin))
    runtime = portable.inspect_project_sql_emission(artifact, artifact.request)
    assert [(r.start, r.end, r.kind, r.role) for r in runtime.ranges] == [
        (r.start, r.end, r.kind, r.role) for r in view.ranges
    ]


# -- values, parameters and UTF-8 ranges ------------------------------------


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_fixed_values_signs_parameters_and_utf8_ranges(tmp_path_factory, target):
    _, bound = _observed(tmp_path_factory, target, "R_fixed_direct", "table_bind")
    _, kept = _observed(tmp_path_factory, target, "R_fixed_direct", "table_preserve")
    document = json.loads(bound)
    fixed = [f["value"] for f in _records(document, "fixed_value")]
    assert {"tag": "Int", "value": "9007199254740993"} in fixed
    # Signed zero and every sign stay unary structure over an unsigned leaf.
    assert fixed.count({"tag": "Float", "value": "0x0.0p+0"}) == 2
    assert not any(str(f["value"]).startswith("-") for f in fixed)
    assert {"tag": "Bool", "value": True} in fixed
    assert fixed.count({"tag": "Int", "value": "17"}) == 2
    assert len(_records(document, "sql_unary")) == 5
    assert {u["operator"] for u in _records(document, "sql_unary")} == {"+", "-"}
    uses = [
        _record(document, ref)
        for ref in _records(document, "artifact")[0]["parameter_uses"]
    ]
    indexes = [use["server_index"] for use in uses]
    if target == "mysql":
        assert indexes == list(range(1, len(uses) + 1))
    else:
        by_slot: dict[str, set[int]] = {}
        for use in uses:
            by_slot.setdefault(json.dumps(use["slot"]), set()).add(use["server_index"])
        assert all(len(v) == 1 for v in by_slot.values())
        assert sorted({i for v in by_slot.values() for i in v}) == list(
            range(1, len(by_slot) + 1)
        )
    literal = json.loads(kept)
    values = [leaf["value"] for leaf in _records(literal, "sql_literal")]
    assert {"tag": "Text", "value": "雪é😀"} in values
    assert {"tag": "Text", "value": "\"'\\\n"} in values
    for data in (bound, kept):
        view = pure.parse_emission_observation(data).view
        assert view is not None
        text = view.sql.decode("utf-8")
        chars = 0
        for token in (r for r in view.ranges if r.kind != "expression_range"):
            piece = view.sql[token.start : token.end].decode("utf-8")
            assert len(text[:chars].encode("utf-8")) == token.start
            chars += len(piece)
        assert chars == len(text)
    unicode_doc = json.loads(
        _observed(tmp_path_factory, target, "X_aggregate_grouped", "hidden")[1]
    )
    sql = _records(unicode_doc, "rendered")[0]["sql"]
    assert "é" in sql and len(sql.encode("utf-8")) > len(sql)
    json_text = json.dumps(sql, ensure_ascii=False)
    assert len(json_text.encode("utf-8")) != len(sql.encode("utf-8"))


def test_source_associations_keep_paths_hops_and_partial_locations(tmp_path_factory):
    availability: set[str] = set()
    hops = paths = 0
    for case, variant in (
        ("N_imported_chain", "bag"),
        ("R_fixed_direct", "table_bind"),
        ("A_window_qualify", "hidden"),
    ):
        document = json.loads(_observed(tmp_path_factory, "postgres", case, variant)[1])
        for association in _records(document, "association"):
            availability.add(association["location"]["availability"])
            paths += association["path"] is not None
            hops += association["hop"] is not None or bool(
                association["path"] and association["path"]["hops"]
            )
        for origin in _records(document, "origin"):
            assert origin["ref"]["kind"] == "origin"
    assert {"complete"} <= availability
    assert paths and hops


# -- raw boundary, closed rejections and resources ---------------------------


def test_raw_boundary_rejections_are_closed_and_bounded(tmp_path_factory):
    _, data = _observed(tmp_path_factory, "postgres", "N_imported_chain", "bag")
    text = data.decode("utf-8")
    cases = {
        b"": pure.Status.INVALID_JSON,
        b"\xff": pure.Status.INVALID_UTF8,
        data + b"{}": pure.Status.INVALID_JSON,
        data.replace(schema.FORMAT.encode(), b"pietto.sql-emission.v1", 1): (
            pure.Status.UNKNOWN_FORMAT
        ),
        text.replace('"root":', '"root":1,"root":', 1).encode(): (
            pure.Status.DUPLICATE_KEY
        ),
        text.replace(
            '"fields":{', '"fields":{"family":"x","family":"x",', 1
        ).encode(): (pure.Status.DUPLICATE_KEY),
        text.replace('"root":["artifact",0]', '"root":["artifact",0.0]', 1).encode(): (
            pure.Status.INVALID_VALUE
        ),
        text.replace('"root":["artifact",0]', '"root":["artifact",NaN]', 1).encode(): (
            pure.Status.INVALID_VALUE
        ),
        text.replace('"root":["artifact",0]', '"root":["artifact",-1]', 1).encode(): (
            pure.Status.INVALID_VALUE
        ),
        text.replace(
            '"root":["artifact",0]', '"root":["artifact",false]', 1
        ).encode(): (pure.Status.INVALID_REF),
        text.replace(
            '"root":["artifact",0]', '"root":["artifact",99999999999]', 1
        ).encode(): (pure.Status.RESOURCE_LIMIT),
    }
    for raw, status in cases.items():
        assert _status(raw)[0] is status, raw[:60]
    assert _status(text.encode())[0] is OK
    assert pure.parse_emission_observation(text).status is OK
    assert pure.parse_emission_observation(123).status is pure.Status.INVALID_INPUT  # type: ignore[arg-type]
    deep = ("[" * (schema.MAX_DEPTH + 1) + "]" * (schema.MAX_DEPTH + 1)).encode()
    assert _status(deep) == (pure.Status.RESOURCE_LIMIT, "JSON depth")
    rejected = pure.parse_emission_observation(b"\xff" * 64)
    assert rejected.detail is not None and len(rejected.detail) <= 64
    assert "\\xff" not in repr(rejected)


def test_resource_limits_reject_before_success(tmp_path_factory, monkeypatch):
    artifact, data = _observed(tmp_path_factory, "mysql", "N_imported_chain", "bag")
    for name, value, detail in (
        ("MAX_DOCUMENT_BYTES", len(data) - 1, "document size"),
        ("MAX_JSON_VALUES", 100, "JSON values"),
        ("MAX_RECORDS", 10, "records"),
        ("MAX_EDGES", 10, "reference edges"),
        ("MAX_TEXT_BYTES", 8, "text size"),
    ):
        with monkeypatch.context() as patch:
            patch.setattr(schema, name, value)
            assert _status(data) == (pure.Status.RESOURCE_LIMIT, detail), name
    with monkeypatch.context() as patch:
        patch.setattr(schema, "MAX_RECORDS", 10)
        refused = portable.export_emission_observation(artifact, artifact.request)
        assert refused == portable.EmissionObservation(
            portable.ObservationStatus.RESOURCE_LIMIT
        )
    from pietto._project.project_sql_emission import (
        EmissionOutcome,
        serialize_project_sql_emission,
    )

    # A private transport limit never changes the public emission.
    with monkeypatch.context() as patch:
        patch.setattr(schema, "MAX_DOCUMENT_BYTES", 16)
        assert (
            portable.export_emission_observation(artifact, artifact.request).status
            is portable.ObservationStatus.RESOURCE_LIMIT
        )
        public = serialize_project_sql_emission(
            EmissionOutcome(
                "VERIFIED",
                artifact.request.verification.completed.diagnostics,
                artifact,
            )
        )
        assert json.loads(public)["status"] == "VERIFIED"


def test_mapping_route_is_bounded_builtin_only_and_not_duplicate_evidence(
    tmp_path_factory,
):
    _, data = _observed(tmp_path_factory, "postgres", "W_join_shapes", "semi")
    value = json.loads(data)
    assert pure.evaluate_emission_observation(value).canonical_bytes == data
    cyclic = json.loads(data)
    cyclic["records"][0]["fields"]["diagnostics"] = cyclic["records"]
    assert (
        pure.evaluate_emission_observation(cyclic).status is pure.Status.INVALID_INPUT
    )
    shaped = json.loads(data)
    shaped["root"] = ("artifact", 0)
    assert (
        pure.evaluate_emission_observation(shaped).status is pure.Status.INVALID_INPUT
    )

    class Loud(dict):
        def items(self):  # pragma: no cover - must never be called
            raise AssertionError("user method called")

    assert (
        pure.evaluate_emission_observation(Loud(value)).status
        is pure.Status.INVALID_INPUT
    )
    floated = json.loads(data)
    floated["records"][0]["ref"][1] = 0.0
    assert (
        pure.evaluate_emission_observation(floated).status is pure.Status.INVALID_INPUT
    )
    for bad in (None, [], "text", b"bytes", 1):
        assert pure.evaluate_emission_observation(bad).status is not OK
    duplicated = data.decode().replace('"root":', '"root":"x","root":', 1)
    assert _status(duplicated.encode())[0] is pure.Status.DUPLICATE_KEY
    # json.loads keeps the last duplicate; the parsed route cannot see it.
    assert pure.evaluate_emission_observation(json.loads(duplicated)).status is OK


# -- structural mutations -----------------------------------------------------


def _mutated(data: bytes, edit, *, recanonical=False) -> bytes:
    document = json.loads(data)
    edit(document)
    return _encode(_recanonical(document) if recanonical else document)


def test_schema_ref_order_and_sharing_mutations_reject(tmp_path_factory):
    artifact, data = _observed(
        tmp_path_factory, "postgres", "S_set_nesting", "left_fold_except"
    )

    def first(document, kind):
        return next(r for r in document["records"] if r["ref"][0] == kind)

    def drop_field(d):
        del first(d, "sql_symbol")["fields"]["name"]

    def extra_field(d):
        first(d, "sql_symbol")["fields"]["extra"] = 1

    def reorder_fields(d):
        fields = first(d, "sql_symbol")["fields"]
        first(d, "sql_symbol")["fields"] = dict(reversed(fields.items()))

    def unknown_kind(d):
        d["records"][-1]["ref"][0] = "sql_mystery"

    def bool_ordinal(d):
        first(d, "sql_symbol")["fields"]["position"] = True

    def dangling(d):
        first(d, "artifact")["fields"]["rendered"] = ["rendered", 5]

    def foreign_domain(d):
        first(d, "artifact")["fields"]["rendered"] = ["request", 0]

    def swap_records(d):
        d["records"][1], d["records"][2] = d["records"][2], d["records"][1]

    def duplicate_record(d):
        d["records"].append(json.loads(json.dumps(d["records"][-1])))

    def orphan(d):
        d["records"].append(
            {"ref": ["owner", 99], "fields": first(d, "owner")["fields"]}
        )

    def plan_kind(d):
        first(d, "sql_symbol")["fields"]["binding"] = {
            "kind": "nonsense",
            "position": 0,
        }

    for edit, status in (
        (drop_field, pure.Status.INVALID_FIELD),
        (extra_field, pure.Status.INVALID_FIELD),
        (reorder_fields, pure.Status.INVALID_FIELD),
        (unknown_kind, pure.Status.INVALID_RECORD),
        (bool_ordinal, pure.Status.INVALID_VALUE),
        (dangling, pure.Status.INVALID_REF),
        (foreign_domain, pure.Status.INVALID_REF),
        (swap_records, pure.Status.INVALID_REF),
        (duplicate_record, pure.Status.INVALID_REF),
        (orphan, pure.Status.INVALID_REF),
        (plan_kind, pure.Status.INVALID_REF),
    ):
        assert _status(_mutated(data, edit))[0] is status, edit.__name__

    # SET positional alignment is identity: a split shared read is rejected.
    def split_alignment(d):
        column = _records(d, "set_column")[0]
        column["inputs"] = list(reversed(column["inputs"]))

    assert _status(_mutated(data, split_alignment)) == (
        pure.Status.INVALID_RELATION,
        "set positional alignment",
    )

    # Erasing a sharing the relations do not constrain stays internally
    # consistent, and only runtime correspondence sees the difference.
    def unshare(d):
        references = [r for r in d["records"] if r["ref"][0] == "sql_stage_reference"]
        target = next((r for r in references if r["fields"]["realization"]), None)
        if target is None:
            realized = next(r for r in d["records"] if r["ref"][0] == "stage_column")
            target = realized
        copy = {
            "ref": ["realization", 10**4],
            "fields": dict(_record(d, target["fields"]["realization"])),
        }
        d["records"].append(copy)
        target["fields"]["realization"] = ["realization", 10**4]

    unshared = _mutated(data, unshare, recanonical=True)
    assert _status(unshared)[0] is OK
    issues = portable.verify_emission_observation(
        unshared, artifact, artifact.request
    ).issues
    assert issues and issues[0] in {"record_sharing", "record_binding"}


def test_sql_only_and_sidecar_only_corruptions_reject(tmp_path_factory):
    _, data = _observed(
        tmp_path_factory, "postgres", "R_fixed_direct", "table_preserve"
    )
    document = json.loads(data)
    events = _events(document)
    rendered = _records(document, "rendered")[0]
    sql = rendered["sql"]
    raw = sql.encode("utf-8")

    def replace_at(token, text):
        start, end = token["start"], token["end"]
        assert len(text.encode()) == end - start
        return (raw[:start] + text.encode() + raw[end:]).decode("utf-8")

    def with_sql(new_sql):
        def edit(d):
            _records(d, "rendered")[0]["sql"] = new_sql

        return _mutated(data, edit)

    label = next(e for e in events if e["role"] == "label")
    name = raw[label["start"] + 1 : label["end"] - 1].decode()
    swapped = name[:-1] + ("x" if name[-1] != "x" else "y")
    separator = next(e for e in events if e["role"] == "separator")
    anchor = next(e for e in events if e["role"] == "anchor_open")
    unary = next(
        e
        for e in events
        if e["role"] == "unary_open" and raw[e["start"] : e["end"]] == b"(-"
    )
    unary_position = events.index(unary)
    following = events[unary_position + 1]
    for new_sql, detail in (
        (replace_at(label, '"' + swapped + '"'), "output labels"),
        (replace_at(separator, " ,"), "syntax spelling"),
        (replace_at(anchor, "CAST["), "parenthesis balance"),
        (
            replace_at(unary, "(+"),
            "operator spelling",
        ),
        (
            replace_at(
                following, "-" + raw[following["start"] + 1 : following["end"]].decode()
            ),
            "comment forming",
        ),
    ):
        assert _status(with_sql(new_sql)) == (pure.Status.INVALID_RELATION, detail)

    def shift(d):
        rows = _records(d, "event")
        rows[3]["end"] += 1
        rows[4]["start"] += 1

    assert _status(_mutated(data, shift))[0] is pure.Status.INVALID_RELATION

    def drop_token(d):
        _records(d, "rendered")[0]["events"].pop(5)

    assert _status(_mutated(data, drop_token, recanonical=True)) == (
        pure.Status.INVALID_RELATION,
        "token coverage",
    )

    def overlay_end(d):
        overlay = _record(d, _records(d, "rendered")[0]["expression_ranges"][0])
        overlay["end"] -= 1

    assert _status(_mutated(data, overlay_end))[0] is pure.Status.INVALID_RELATION

    def role_swap(d):
        for row in _records(d, "event"):
            if row["role"] == "separator":
                row["role"] = "cte_separator"
                return

    assert _status(_mutated(data, role_swap))[0] is not OK


def test_mid_codepoint_and_parameter_corruptions_reject(tmp_path_factory):
    _, data = _observed(tmp_path_factory, "postgres", "X_aggregate_grouped", "hidden")
    document = json.loads(data)
    raw = _records(document, "rendered")[0]["sql"].encode()
    position = raw.index("é".encode())
    rows = _records(document, "event")
    index = next(i for i, e in enumerate(rows) if e["start"] <= position < e["end"])

    def split(d):
        events = _records(d, "event")
        events[index]["end"] = position + 1
        events[index + 1]["start"] = position + 1

    assert _status(_mutated(data, split)) == (
        pure.Status.INVALID_RELATION,
        "UTF-8 boundary",
    )
    _, bound = _observed(tmp_path_factory, "postgres", "R_fixed_direct", "table_bind")

    def index_drift(d):
        _records(d, "native_use")[0]["server_index"] += 1

    assert _status(_mutated(bound, index_drift))[0] is pure.Status.INVALID_RELATION
    text = json.loads(bound)
    parameter = next(e for e in _events(text) if e["kind"] == "parameter")
    sql = _records(text, "rendered")[0]["sql"].encode()
    token = sql[parameter["start"] : parameter["end"]].decode()
    changed = token[:-1] + ("9" if token[-1] != "9" else "8")

    def token_drift(d):
        rendered = _records(d, "rendered")[0]
        rendered["sql"] = (
            sql[: parameter["start"]] + changed.encode() + sql[parameter["end"] :]
        ).decode()

    assert _status(_mutated(bound, token_drift)) == (
        pure.Status.INVALID_RELATION,
        "parameter token",
    )
    _, mysql = _observed(tmp_path_factory, "mysql", "R_fixed_direct", "table_bind")

    def mysql_index(d):
        _records(d, "native_use")[1]["server_index"] = 1

    assert _status(_mutated(mysql, mysql_index)) == (
        pure.Status.INVALID_RELATION,
        "mysql parameter index",
    )

    def bool_as_int(d):
        for value in _records(d, "fixed_value"):
            if value["value"]["tag"] == "Bool":
                value["value"] = {"tag": "Int", "value": "1"}
                return

    assert _status(_mutated(bound, bool_as_int))[0] is pure.Status.INVALID_RELATION


def test_requirement_inventory_mutations_reject(tmp_path_factory):
    artifact, data = _observed(
        tmp_path_factory, "postgres", "A_window_qualify", "hidden"
    )

    def generated(d):
        return _records(d, "artifact")[0]["generated_requirements"]

    def delete_one(d):
        generated(d).pop(3)

    def delete_with_cause_kept(d):
        items = generated(d)
        kinds = [_record(d, ref)["kind"] for ref in items]
        target = kinds.index("window_computation")
        del items[target : target + 2]

    def duplicate(d):
        items = generated(d)
        items.insert(1, items[0])

    def reorder(d):
        items = generated(d)
        items[0], items[1] = items[1], items[0]

    def scan_premises(d):
        for ref in generated(d):
            item = _record(d, ref)
            if item["kind"] == "qualified_scan":
                item["premises"] = item["premises"][:-1]
                return

    def premise_scope(d):
        for ref in generated(d):
            item = _record(d, ref)
            if item["kind"] == "source_representation":
                item["premises"] = item["premises"][1:]
                return

    for edit, detail in (
        (delete_one, "generated inventory size"),
        (delete_with_cause_kept, "generated inventory size"),
        (duplicate, "generated inventory size"),
        (reorder, "generated inventory entry"),
        (scan_premises, "generated premises"),
        (premise_scope, "generated premise scope"),
    ):
        assert _status(_mutated(data, edit, recanonical=True)) == (
            pure.Status.INVALID_RELATION,
            detail,
        ), edit.__name__

    def delete_original(d):
        _records(d, "artifact")[0]["original_requirements"].pop(2)

    def coordinated_original(d):
        items = _records(d, "artifact")[0]["original_requirements"]
        kept = [
            ref
            for ref in items
            if not (
                _record(d, ref)["family"] == "expression"
                and _record(d, ref)["subject"]
                == _records(d, "sql_stage_reference")[0]["original"]
            )
        ]
        assert len(kept) < len(items)
        for position, ref in enumerate(kept):
            _record(d, ref)["entry"] = {"kind": "demand", "position": position}
        items[:] = kept

    assert _status(_mutated(data, delete_original, recanonical=True)) == (
        pure.Status.INVALID_RELATION,
        "original inventory entry",
    )
    assert _status(_mutated(data, coordinated_original, recanonical=True)) == (
        pure.Status.INVALID_RELATION,
        "original expression demand",
    )


def test_order_carriers_c32_and_coherent_alternatives(tmp_path_factory):
    carriers = {}
    documents = {}
    for variant in ("order_ordinary", "order_rebound", "order_completed"):
        artifact, data = _observed(
            tmp_path_factory, "postgres", "O_named_later", variant
        )
        document = json.loads(data)
        documents[variant] = (artifact, data)
        (order,) = _records(document, "result_order")
        carriers[variant] = order["carrier"]
        items = [_record(document, ref) for ref in order["items"]]
        assert {item["carrier"] for item in items} == {order["carrier"]}
        results = _records(document, "row_result_body")
        visible = {
            json.dumps(_record(document, c)["output"])
            for body in results
            for c in body["columns"]
        }
        # The ORDER value image is the scanned stage's carrier, never an output.
        assert all(json.dumps(item["port"]) not in visible for item in items)
    assert carriers == {
        "order_ordinary": "ordinary",
        "order_rebound": "rebound",
        "order_completed": "completed",
    }
    artifact, data = documents["order_rebound"]

    def one_item(d):
        _records(d, "result_order_item")[0]["carrier"] = "ordinary"

    def coordinated(d):
        _records(d, "result_order")[0]["carrier"] = "ordinary"
        for item in _records(d, "result_order_item"):
            item["carrier"] = "ordinary"

    def wrong_output(d):
        item = _records(d, "result_order_item")[0]
        item["port"] = _records(d, "row_result_body")[0]["terminals"][0]

    def wrong_read(d):
        item = _records(d, "result_order_item")[0]
        body = _record(d, _records(d, "row_result_use")[0]["body"])
        item["read"] = _record(d, body["columns"][0])["column"]

    assert _status(_mutated(data, one_item)) == (
        pure.Status.INVALID_RELATION,
        "order item",
    )
    assert _status(_mutated(data, wrong_output)) == (
        pure.Status.INVALID_RELATION,
        "overlay carrier",
    )
    assert _status(_mutated(data, wrong_read))[0] is pure.Status.INVALID_RELATION
    coherent = _mutated(data, coordinated)
    assert _status(coherent)[0] is OK
    assert portable.verify_emission_observation(
        coherent, artifact, artifact.request
    ).issues == ("field_text",)
    # A genuinely different, internally consistent observation is not the
    # runtime roots it is offered for.
    other_artifact, other = documents["order_ordinary"]
    assert _status(other)[0] is OK
    assert not portable.verify_emission_observation(
        other, artifact, artifact.request
    ).corresponds
    assert portable.verify_emission_observation(
        other, other_artifact, other_artifact.request
    ).corresponds


def test_set_forms_join_membership_and_result_boundaries(tmp_path_factory):
    spellings = set()
    for variant in emission.VARIANTS["S_set_forms"]:
        document = json.loads(
            _observed(tmp_path_factory, "mysql", "S_set_forms", variant)[1]
        )
        (unit,) = _records(document, "set_body")
        spellings.add(schema.set_spelling(unit["kind"], unit["quantifier"]))
        for column in _records(document, "set_column"):
            assert len(column["inputs"]) == len(unit["operands"])
    assert len(spellings) == 6
    document = json.loads(
        _observed(tmp_path_factory, "postgres", "S_set_nesting", "left_fold_except")[1]
    )
    assert [u["kind"] for u in _records(document, "set_body")].count("except") >= 1
    assert all(len(u["operands"]) >= 2 for u in _records(document, "set_body"))
    semi = json.loads(
        _observed(tmp_path_factory, "postgres", "W_join_shapes", "semi")[1]
    )
    (join,) = _records(semi, "join_body")
    assert join["membership"] == "exists" and join["sentinel"] is not None
    outer = json.loads(
        _observed(tmp_path_factory, "postgres", "W_join_values", "left_marker")[1]
    )
    nulled = [c for c in _records(outer, "join_column") if c["nulling"]]
    assert nulled
    for column in nulled:
        realization = _record(outer, _record(outer, column["column"])["realization"])
        assert realization["nullable"] is True
    artifact, data = _observed(
        tmp_path_factory, "postgres", "W_join_values", "left_marker"
    )

    def not_null(d):
        column = next(c for c in _records(d, "join_column") if c["nulling"])
        stage = _record(d, column["column"])
        _record(d, stage["realization"])["nullable"] = False

    assert _status(_mutated(data, not_null))[0] is pure.Status.INVALID_RELATION
    hidden = json.loads(
        _observed(tmp_path_factory, "mysql", "A_window_qualify", "hidden")[1]
    )
    assert any(not c["selected"] for c in _records(hidden, "window_column"))
    assert any(b["block_kind"] == "qualify" for b in _records(hidden, "row_body"))
    limited = json.loads(
        _observed(tmp_path_factory, "postgres", "O_result_limit", "zero")[1]
    )
    assert [limit["value"] for limit in _records(limited, "result_limit")] == [0]


# -- runtime refusals, correspondence and refusal to reconstruct -------------


def test_runtime_roots_decoded_data_and_tampering_are_refused(tmp_path_factory):
    artifact, data = _observed(tmp_path_factory, "postgres", "N_imported_chain", "bag")
    other, _ = _observed(tmp_path_factory, "postgres", "R_fixed_direct", "table_bind")
    view = pure.parse_emission_observation(data).view
    invalid = portable.EmissionObservation(portable.ObservationStatus.INVALID_ROOT)
    for roots in (
        (None, None),
        (view, artifact.request),
        (json.loads(data), artifact.request),
        (artifact, other.request),
        (artifact, None),
    ):
        assert portable.export_emission_observation(*roots) == invalid
        assert portable.verify_emission_observation(data, *roots).issues == (
            "invalid_runtime_root",
        )
    item = emission.fixture("postgres", "N_imported_chain", "bag")
    root = tmp_path_factory.mktemp("slice14-tampered")
    tampered = emission.build_case(
        root, item["source"], item["contract"], item["policy"]
    )[1].artifact
    assert tampered is not None
    object.__setattr__(tampered.rendered, "sql", tampered.rendered.sql + b" ")
    assert portable.export_emission_observation(tampered, tampered.request) == (
        portable.EmissionObservation(portable.ObservationStatus.UNVERIFIED)
    )
    assert portable.verify_emission_observation(
        data, tampered, tampered.request
    ).issues == ("unverified_artifact",)
    assert portable.verify_emission_observation(
        b"{}", artifact, artifact.request
    ).issues == ("document_invalid_document",)
    fresh = emission.build_case(
        tmp_path_factory.mktemp("slice14-fresh"),
        item["source"],
        item["contract"],
        item["policy"],
    )[1].artifact
    assert fresh is not None
    again = portable.export_emission_observation(fresh, fresh.request).canonical_bytes
    assert again == data

    def diagnostics(d):
        _records(d, "artifact")[0]["diagnostics"] = [{"code": "PIE-X0000"}]

    assert portable.verify_emission_observation(
        _mutated(data, diagnostics), artifact, artifact.request
    ).issues == ("field_data", "public_diagnostics")


def test_correspondence_shape_faults_stay_closed_issues(tmp_path_factory, monkeypatch):
    artifact, data = _observed(tmp_path_factory, "postgres", "W_join_shapes", "semi")

    # Injected runtime defect: a runtime value outside the closed schema must
    # become a closed issue, never an escaping exception.
    def outside(_value):
        raise portable._Outside

    monkeypatch.setattr(portable, "_plan", outside)
    issues = portable.verify_emission_observation(
        data, artifact, artifact.request
    ).issues
    assert issues and set(issues) <= {
        "record_binding",
        "public_projection",
        "inspection_projection",
    }


def test_verification_and_lookup_refuse_to_reconstruct(tmp_path_factory, monkeypatch):
    artifact, data = _observed(tmp_path_factory, "mysql", "A_window_qualify", "hidden")
    from pietto._project import check
    from pietto._project import project_sql_emission as emitting
    from pietto._project import project_sql_emission_ast as sql_ast
    from pietto._project import project_sql_emission_contract as contract
    from pietto._project import project_sql_emission_rendering as rendering
    from pietto._project import project_sql_plan

    def refuse(*_args, **_kwargs):
        raise AssertionError("reconstruction entrypoint called")

    # The inherited complete verifier re-derives its row blockers through its own
    # realization helper (`project_sql_emission_ast.realize_rows`); that internal
    # step stays enabled. Everything correspondence itself could reach is not.
    for module, name in (
        (contract, "prepare_project_sql_emission"),
        (emitting, "prepare_project_sql_emission"),
        (emitting, "emit_project_sql"),
        (emitting, "realize_project_sql"),
        (emitting, "build_sql_ast"),
        (emitting, "realize_rows"),
        (emitting, "render_sql"),
        (emitting, "render_row_sql"),
        (emitting, "render_join_sql"),
        (sql_ast, "build_sql_ast"),
        (rendering, "render_sql"),
        (rendering, "render_row_sql"),
        (rendering, "render_join_sql"),
        (check, "check_project_parse_only"),
        (project_sql_plan, "build_project_sql_plan"),
        (portable, "export_emission_observation"),
    ):
        monkeypatch.setattr(module, name, refuse)
    decoded = pure.parse_emission_observation(data)
    assert decoded.status is OK and decoded.view is not None
    assert decoded.view.at(0)
    assert portable.verify_emission_observation(
        data, artifact, artifact.request
    ).corresponds


# -- the real process family --------------------------------------------------


def _independent_manifest(interpreters):
    """Phase66 rows derived here, never from the production registry."""
    rows = []
    for version in interpreters:
        label = f"python{version[0]}.{version[1]}"
        for seed in SEEDS:
            key = f"source:{label}:seed:{seed}"
            rows.append(("phase66", key, version, seed, "checkout", key))
    for mode in ("relocated", "installed"):
        for version in interpreters:
            key = f"{mode}:python{version[0]}.{version[1]}:seed:7"
            rows.append(("phase66", key, version, "7", mode, key))
    return tuple(rows)


def test_process_registry_and_independent_manifests():
    import _pietto_differential_probe_batch as batch
    import _pietto_differential_process_acquisition as process
    from test_phase65_slice14_portable_boundary_minimal_process_integration import (
        _available_request_manifest,
    )

    assert process.FAMILY_ORDER[-1] == "phase66"
    assert batch.FAMILY_MODULES["phase66"] == (
        "_pietto_phase66_sql_emission_differential_probe"
    )
    assert batch.FAMILY_AMBIENT["phase66"] == "PIETTO_PHASE66_SLICE14_AMBIENT"
    assert "phase66" not in batch.CLI_SESSION_FAMILIES
    assert batch.PHASE66_MODULES == (
        "pietto._project.project_sql_emission_portable",
        "pietto._project.project_sql_emission_portable_schema",
        "pietto._project.project_sql_emission_pure_boundary",
    )
    assert process.RELOCATION_SUPPORT_MANIFEST[-2:] == (
        "_pietto_phase66_sql_emission_probe.py",
        "_pietto_phase66_sql_emission_differential_probe.py",
    )
    current = (sys.version_info.major, sys.version_info.minor)
    for interpreters, total, cells in (
        ({current: sys.executable}, 61, 9),
        ({(3, 13): "3.13", (3, 12): "3.12"}, 98, 16),
        ({(3, 12): "3.12", (3, 13): "3.13"}, 98, 16),
    ):
        actual = tuple(
            (r.family, r.key, r.cell.version, r.cell.seed, r.cell.mode, r.ambient)
            for r in process.all_requests(interpreters)
        )
        expected = _available_request_manifest(interpreters)
        assert actual == expected
        assert tuple(r for r in actual if r[0] == "phase66") == _independent_manifest(
            interpreters
        )
        assert len(actual) == total and len(process.cell_plan(interpreters)) == cells
        historical = [r for r in actual if r[0] != "phase66"]
        assert len(historical) == total - 6 * len(interpreters)


def test_acquired_phase66_cells_same_child_origins_and_identical_bytes(
    tmp_path_factory, record_property
):
    import _pietto_differential_probe_batch as batch
    import _pietto_differential_process_acquisition as process

    store = process.acquisition(tmp_path_factory)
    expected = _independent_manifest(store.interpreters)
    documents = store.documents("phase66")
    assert tuple(documents) == tuple(row[1] for row in expected)
    assert len(set(documents.values())) == 1
    observed = json.loads(next(iter(documents.values())))
    assert (
        observed["format"] == "pietto.phase66-sql-emission-observation-differential.v1"
    )
    assert len(observed["cases"]) == 22
    assert {case["status"] for case in observed["cases"]} == {
        "VERIFIED",
        "INPUT_REJECTED",
        "BLOCKED",
    }
    for case in observed["cases"]:
        if case["status"] == "VERIFIED":
            data = case["document"].encode()
            assert pure.parse_emission_observation(data).canonical_bytes == data
        else:
            assert (
                "document" not in case
                and json.loads(case["public"])["artifact"] is None
            )
    for request in process.family_requests("phase66", store.interpreters):
        origins = store.phase66_module_import_origins(request.cell)
        assert tuple(origins) == batch.PHASE66_MODULES
        _, source_root = store._cell_child(request.cell)
        for name, origin in origins.items():
            expected_file = (
                source_root / "src" / Path(*name.split(".")).with_suffix(".py")
            )
            assert origin == expected_file.resolve()
            if request.cell.mode != "checkout":
                assert not origin.is_relative_to(process.REPO_ROOT)
        if request.cell.mode == "installed":
            assert store.import_origin(request.cell).is_relative_to(
                store.installed_source_root()
            )
    record_property("phase66_request_manifest", json.dumps(expected))


@pytest.mark.parametrize("mode", ("checkout", "relocated", "installed"))
def test_standalone_forward_reverse_batches_beside_older_families(
    tmp_path, tmp_path_factory, mode
):
    import _pietto_differential_probe_batch as batch
    import _pietto_differential_process_acquisition as process

    store = process.acquisition(tmp_path_factory)
    version = (sys.version_info.major, sys.version_info.minor)
    child, source_root = store._cell_child(process.Cell(version, "7", mode))
    families = ("phase65", "phase66")
    standalone = {}
    for family in families:
        script = child.parent / (batch.FAMILY_MODULES[family] + ".py")
        result = subprocess.run(
            (
                sys.executable,
                str(script),
                "--workspace",
                str(tmp_path / "alone" / family),
            ),
            cwd=tmp_path,
            env=store.environment(source_root, "7", family + "-parity"),
            capture_output=True,
        )
        assert result.returncode == 0 and result.stderr == b"", result.stderr[-2000:]
        assert result.stdout.endswith(b"\n") and not result.stdout.endswith(b"\n\n")
        standalone[family] = result.stdout
    for label, order in (("forward", families), ("reverse", tuple(reversed(families)))):
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
        assert result.returncode == 0 and result.stdout == b"", result.stderr[-2000:]
        payload = json.loads(output.read_bytes())
        assert {
            key: base64.b64decode(value) for key, value in payload["results"].items()
        } == standalone
        assert tuple(payload["module_import_origins"]) == batch.PHASE65_MODULES
        assert tuple(payload["phase66_module_import_origins"]) == batch.PHASE66_MODULES
        for name, origin in payload["phase66_module_import_origins"].items():
            assert (
                Path(origin)
                == (
                    source_root / "src" / Path(*name.split(".")).with_suffix(".py")
                ).resolve()
            )
    broken = tmp_path / "broken"
    (broken / "postgres" / "N_imported_chain").mkdir(parents=True)
    (broken / "postgres" / "N_imported_chain" / "bag").write_text("not a directory")
    script = child.parent / (batch.FAMILY_MODULES["phase66"] + ".py")
    result = subprocess.run(
        (sys.executable, str(script), "--workspace", str(broken)),
        cwd=tmp_path,
        env=store.environment(source_root, "7", "failure"),
        capture_output=True,
    )
    assert result.returncode == 1 and result.stdout == b""
    assert result.stderr == b"Phase66 private observation probe failed.\n"


def _expression_premise(item, outcome, target):
    contract = json.loads(item["contract"])
    site = outcome.artifact.request.plan.expression_sites[0]
    contract["environment"].append(
        {
            "key": "encoding",
            "scope": {
                "kind": "expression",
                "source": contract["sources"][0]["selector"],
                "site": {"kind": site.ref.kind.value, "position": site.ref.position},
                "context": {
                    "kind": site.block.kind.value,
                    "position": site.block.position,
                },
            },
            "value": "UTF8" if target == "postgres" else "utf8mb4",
        }
    )
    return emission.encoded(contract)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_variants_outside_the_generation_corpus_have_real_witnesses(
    tmp_path_factory, target
):
    from pietto._project.project_sql_emission import emit_project_sql

    # A multi-hop path JOIN is the only source of predecessor JOIN inputs. It
    # stays outside the admitted emission domain, so it has no artifact and no
    # private document; the exporter refuses its outcome.
    item = emission.join_witness(
        target,
        "query result:\n    from lhs\n"
        "    inner join lhs as r:\n        from lhs\n"
        "        via link: l -> r\n        via link: r -> l\n"
        "    select:\n        a = lhs.id\n",
        link=True,
    )
    _, chained = emission.build_case(
        tmp_path_factory.mktemp("slice14-chained"),
        item["source"],
        item["contract"],
        item["policy"],
    )
    assert chained.status == "BLOCKED" and chained.artifact is None
    assert any(
        b.code == "PIE-B1003"
        and getattr(getattr(b.subject, "kind", None), "value", None) == "join"
        for b in chained.blockers
    )
    assert portable.export_emission_observation(chained, None).status is (
        portable.ObservationStatus.INVALID_ROOT
    )

    def observe(checked_outcome):
        artifact = checked_outcome.artifact
        data = portable.export_emission_observation(
            artifact, artifact.request
        ).canonical_bytes
        assert data is not None
        assert portable.verify_emission_observation(
            data, artifact, artifact.request
        ).corresponds
        return json.loads(data)

    item = emission.join_witness(
        target, "query result:\n    union all:\n        from lhs\n        from rhs\n"
    )
    _, outcome = emission.build_case(
        tmp_path_factory.mktemp("slice14-source-operands"),
        item["source"],
        item["contract"],
        item["policy"],
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    document = observe(outcome)
    operands = _records(document, "set_operand_body")
    assert operands and all(o["source"] is not None for o in operands)
    assert all(o["producer"][0] == "bound_source" for o in operands)
    scans = [
        g
        for g in _records(document, "generated_requirement")
        if g["kind"] == "qualified_scan"
    ]
    assert {g["subject"][0] for g in scans} == {"bound_source"}

    item = emission.fixture(target, "R_fixed_direct", "table_preserve")
    checked, outcome = emission.build_case(
        tmp_path_factory.mktemp("slice14-expression-premise"),
        item["source"],
        item["contract"],
        item["policy"],
    )
    premised = emit_project_sql(checked, _expression_premise(item, outcome, target))
    assert premised.status == "VERIFIED"
    document = observe(premised)
    scoped = [
        p
        for p in _records(document, "premise")
        if type(p["scope"]) is list and type(p["scope"][0]) is list
    ]
    assert len(scoped) == 1
    position = scoped[0]["position"]
    bound = {
        g["kind"]
        for g in _records(document, "generated_requirement")
        if any(_record(document, ref)["position"] == position for ref in g["premises"])
    }
    assert bound == {"source_representation", "field_projection"}
