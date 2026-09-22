"""Real-source emission, independent public consumption and corruption witnesses."""

from copy import copy, deepcopy
from dataclasses import replace
import json

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.project_sql_emission import (
    emit_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_contract import prepare_project_sql_emission
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)


def graft(value, **changes):
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    result = {}
    for target in ("postgres", "mysql"):
        for case in ("G_emission_table_bag", "H_emission_query_bag"):
            item = probe.fixture(target, case)
            checked, outcome = probe.build_case(
                tmp_path_factory.mktemp("emission"),
                item["source"],
                item["contract"],
                item["policy"],
            )
            result[target, case] = (item, checked, outcome)
    return result


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case", ("G_emission_table_bag", "H_emission_query_bag"))
def test_public_vertical(built, target, case):
    item, checked, outcome = built[target, case]
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert public["request"]["literal_policy"] == item["policy"]
    assert [column["label"] for column in public["columns"]] == list(probe.LABELS)
    assert [column["logical_type"]["name"] for column in public["columns"]] == list(
        probe.LOGICAL
    )
    assert [column["correspondence"]["field"] for column in public["columns"]] == [
        2,
        0,
        1,
        3,
        4,
    ]
    assert public["fixed_values"] == public["parameter_uses"] == []
    assert artifact.rendered.sql == public["sql"].encode()
    assert checked.plan.fixed_envelope.values == ()
    assert public["columns"][3]["logical_type"]["parameters"] == {
        "precision": 9,
        "scale": 2,
    }
    assert "opaque.locator" not in public["sql"]
    assert len(artifact.original_requirements) == 27
    assert len(artifact.generated_requirements) == 12
    assert outcome.diagnostics is checked.completed.diagnostics


# Inputs whose only blocker was the not-yet-implemented WHERE family.
MIGRATED_TO_SUCCESS = ("where_later",)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "variant",
    probe.VARIANTS["K_emission_rejected"] + probe.VARIANTS["L_emission_blocked"],
)
def test_real_failure_boundaries(tmp_path, target, variant):
    case = (
        "K_emission_rejected"
        if variant in probe.VARIANTS["K_emission_rejected"]
        else "L_emission_blocked"
    )
    item = probe.fixture(target, case, variant)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    if variant in MIGRATED_TO_SUCCESS:
        # Slice6 implements this input's filter family; the retained source
        # purpose is unchanged and its historical BLOCKED outcome is history.
        assert public["status"] == "VERIFIED"
        assert outcome.artifact is not None
        assert "blockers" not in public
        assert public["sql"] == outcome.artifact.rendered.sql.decode()
        return
    assert public["status"] == ("INPUT_REJECTED" if case.startswith("K") else "BLOCKED")
    assert outcome.artifact is None
    assert set(public) == {
        "format",
        "status",
        "artifact",
        "blockers",
        "diagnostics",
        "cli_errors",
    }
    expected = {
        "missing_source": "PIE-B1001",
        "bool_domain": "PIE-B1002",
        "decimal_mismatch": "PIE-B1002",
        "timestamp_meaning": "PIE-B1004",
        "uuid_meaning": "PIE-B1004",
    }
    if variant in expected:
        assert expected[variant] in [b["code"] for b in public["blockers"]]


@pytest.mark.parametrize(
    "mutation",
    (
        "sql",
        "range",
        "label",
        "source_port",
        "input_port",
        "export",
        "projection_order",
        "original_requirement",
        "generated_requirement",
        "both_requirements",
        "parameter",
    ),
)
def test_independent_correspondence_corruptions(built, mutation):
    _, _, outcome = built["postgres", "G_emission_table_bag"]
    artifact = outcome.artifact
    assert artifact is not None
    ast, rendered = artifact.ast, artifact.rendered
    if mutation == "sql":
        changed = replace(
            artifact,
            rendered=replace(rendered, sql=rendered.sql.replace(b"FROM", b"JOIN")),
        )
    elif mutation == "range":
        changed = replace(
            artifact,
            rendered=replace(
                rendered,
                events=(replace(rendered.events[0], end=True), *rendered.events[1:]),
            ),
        )
    elif mutation in {"label", "source_port", "input_port", "export"}:
        value = "altered" if mutation == "label" else getattr(ast.columns[1], mutation)
        changed = replace(
            artifact,
            ast=replace(
                ast,
                columns=(
                    replace(ast.columns[0], **{mutation: value}),
                    *ast.columns[1:],
                ),
            ),
        )
    elif mutation == "projection_order":
        changed = replace(
            artifact, ast=replace(ast, columns=tuple(reversed(ast.columns)))
        )
    elif mutation == "original_requirement":
        changed = replace(
            artifact, original_requirements=artifact.original_requirements[1:]
        )
    elif mutation == "generated_requirement":
        changed = replace(
            artifact, generated_requirements=artifact.generated_requirements[1:]
        )
    elif mutation == "both_requirements":
        changed = replace(artifact, original_requirements=(), generated_requirements=())
    else:
        changed = replace(artifact, fixed_values=(1,))
    assert not verify_project_sql_emission(changed, artifact.request).verified
    public = probe.decode_public(
        serialize_project_sql_emission(replace(outcome, artifact=changed))
    )
    assert (
        public["status"] == "BLOCKED" and public["blockers"][0]["code"] == "PIE-B1008"
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "missing",
        "extra",
        "duplicate",
        "cross_branch",
        "invented_use",
        "wrong_index",
        "range",
        "requirements",
        "quote",
    ),
)
def test_public_bytes_corruptions(built, mutation):
    _, _, outcome = built["postgres", "G_emission_table_bag"]
    data = serialize_project_sql_emission(outcome)
    document = json.loads(data)
    if mutation == "duplicate":
        data = data.replace(b'"format":', b'"format":"duplicate","format":', 1)
    else:
        if mutation == "missing":
            del document["ranges"]
        elif mutation == "extra":
            document["extra"] = True
        elif mutation == "cross_branch":
            document["artifact"] = None
        elif mutation == "invented_use":
            document["parameter_uses"] = [{"use": 0}]
        elif mutation == "wrong_index":
            document["columns"][0]["ordinal"] = True
        elif mutation == "range":
            document["ranges"][-1]["end"] -= 1
        elif mutation == "requirements":
            document["requirements"] = []
        else:
            document["sql"] = document["sql"].replace('"s0"', "'s0'", 1)
        data = probe.encoded(document)
    with pytest.raises(ValueError):
        probe.decode_public(data)


def test_verification_never_constructs_or_validates_types_again(built, monkeypatch):
    from pietto._project import project_sql_emission_contract as contract
    from pietto._project import project_sql_emission_ast as ast
    from pietto._project import project_sql_emission_rendering as rendering
    from pietto._project import project_sql_emission as emission
    from pietto._project import project_sql_plan as planning

    def forbidden(*args, **kwargs):
        raise AssertionError("construction during inspection")

    _, _, outcome = built["postgres", "G_emission_table_bag"]
    for module, name in (
        (contract, "_decimal_precision_scale_fact"),
        (contract, "prepare_project_sql_emission"),
        (ast, "build_sql_ast"),
        (ast, "build_requirements"),
        (rendering, "render_sql"),
        (planning, "build_project_sql_plan"),
        (emission, "build_sql_ast"),
        (emission, "build_requirements"),
        (emission, "render_sql"),
        (emission, "prepare_project_sql_emission"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    assert (
        probe.decode_public(serialize_project_sql_emission(outcome))["status"]
        == "VERIFIED"
    )


def test_contract_target_root_invalidation(built):
    item, checked, outcome = built["postgres", "G_emission_table_bag"]
    artifact = outcome.artifact
    assert artifact is not None
    document = json.loads(item["contract"])
    document["environment"].append(
        {"key": "session_time_zone", "scope": "statement", "value": "UTC"}
    )
    new_request = prepare_project_sql_emission(checked, probe.encoded(document))
    assert not verify_project_sql_emission(artifact, new_request).verified
    foreign = built["postgres", "H_emission_query_bag"][1]
    assert (
        emit_project_sql(
            graft(checked, completed=foreign.completed), item["contract"].encode()
        ).status
        == "INPUT_REJECTED"
    )


def test_premise_and_resource_failures_have_distinct_codes(built):
    item, checked, _ = built["postgres", "G_emission_table_bag"]
    for premise, code in (
        (
            {"key": "client_encoding", "scope": "statement", "value": "LATIN1"},
            "PIE-B1005",
        ),
        (
            {"key": "resource_limits", "scope": "statement", "value": {"sql_bytes": 1}},
            "PIE-B1007",
        ),
    ):
        document = json.loads(item["contract"])
        document["environment"].append(premise)
        result = emit_project_sql(checked, probe.encoded(document))
        public = probe.decode_public(serialize_project_sql_emission(result))
        assert public["status"] == "BLOCKED"
        assert code in [b["code"] for b in public["blockers"]]


def test_complete_schema_order_and_unused_structure(built):
    item, checked, _ = built["postgres", "G_emission_table_bag"]
    base = json.loads(item["contract"])
    for fields in (
        base["sources"][0]["fields"][:-1],
        list(reversed(base["sources"][0]["fields"])),
    ):
        document = deepcopy(base)
        document["sources"][0]["fields"] = fields
        result = emit_project_sql(checked, probe.encoded(document))
        assert result.status == "BLOCKED" and any(
            b.code == "PIE-B1001" for b in result.blockers
        )


@pytest.mark.parametrize(
    "change,expected",
    (
        ("duplicate_key", "INPUT_REJECTED"),
        ("unknown_key", "INPUT_REJECTED"),
        ("field_duplicate", "INPUT_REJECTED"),
        ("column_duplicate", "INPUT_REJECTED"),
        ("wrong_field_name", "INPUT_REJECTED"),
        ("negative_ordinal", "INPUT_REJECTED"),
        ("row_domain", "INPUT_REJECTED"),
        ("storage_unknown", "INPUT_REJECTED"),
        ("int_range", "BLOCKED"),
        ("nullable", "BLOCKED"),
        ("wrong_storage", "BLOCKED"),
        ("source_family", "BLOCKED"),
        ("row_domain_false", "BLOCKED"),
        ("read_only_false", "BLOCKED"),
        ("long_identifier", "BLOCKED"),
        ("nul_identifier", "BLOCKED"),
        ("target_release", "BLOCKED"),
        ("missing_encoding", "BLOCKED"),
        ("node_limit", "BLOCKED"),
        ("column_limit", "BLOCKED"),
    ),
)
def test_input_and_representation_boundary_matrix(built, change, expected):
    item, checked, _ = built["postgres", "G_emission_table_bag"]
    document = json.loads(item["contract"])
    source = document["sources"][0]
    if change == "duplicate_key":
        data = (
            item["contract"]
            .encode()
            .replace(b'"format":', b'"format":"extra","format":', 1)
        )
    else:
        if change == "unknown_key":
            document["secret"] = "unrecognized"
        elif change == "field_duplicate":
            source["fields"].append(deepcopy(source["fields"][0]))
        elif change == "column_duplicate":
            source["fields"][1]["column"] = source["fields"][0]["column"]
        elif change == "wrong_field_name":
            source["fields"][0]["name"] = "other"
        elif change == "negative_ordinal":
            source["fields"][0]["ordinal"] = -1
        elif change == "row_domain":
            source["scan"] = "only_rows"
        elif change == "storage_unknown":
            source["fields"][0]["representation"]["storage"]["kind"] = "SQL BIGINT"
        elif change == "int_range":
            source["fields"][0]["representation"]["domain"]["max"] = (
                "9223372036854775808"
            )
        elif change == "nullable":
            source["fields"][1]["representation"]["nullable"] = False
        elif change == "wrong_storage":
            source["fields"][0]["representation"]["storage"]["kind"] = "pg_text"
        elif change == "source_family":
            document["target"] = {"family": "mysql", "release": "8.4.12"}
        elif change == "row_domain_false":
            source["premises"][0]["value"] = False
        elif change == "read_only_false":
            source["premises"][1]["value"] = False
        elif change == "long_identifier":
            source["relation"]["name"] = "é" * 32
        elif change == "nul_identifier":
            source["relation"]["name"] = "nul\0name"
        elif change == "target_release":
            document["target"]["release"] = "18.7"
        elif change == "missing_encoding":
            document["environment"] = []
        elif change == "node_limit":
            document["environment"].append(
                {"key": "resource_limits", "scope": "statement", "value": {"nodes": 1}}
            )
        elif change == "column_limit":
            document["environment"].append(
                {
                    "key": "resource_limits",
                    "scope": "statement",
                    "value": {"columns": 4},
                }
            )
        data = probe.encoded(document)
    result = emit_project_sql(checked, data)
    public = probe.decode_public(serialize_project_sql_emission(result))
    assert public["status"] == expected and result.artifact is None


def test_unused_descriptions_bind_but_do_not_require_target_applicability(tmp_path):
    item = probe.fixture("postgres")
    source = item["source"] + '\nsource unused: Row is mysql.table("unrelated")\n'
    document = json.loads(item["contract"])
    unused = deepcopy(document["sources"][0])
    unused["selector"]["name"] = "unused"
    unused["fields"][0]["representation"]["storage"]["kind"] = "my_smallint"
    document["sources"].append(unused)
    checked, result = probe.build_case(tmp_path, source, probe.encoded(document))
    assert result.status == "VERIFIED"
    unused["fields"][0]["ordinal"] = True
    rejected = emit_project_sql(checked, probe.encoded(document))
    assert rejected.status == "INPUT_REJECTED"


@pytest.mark.parametrize("type_expr", ("Decimal", "Decimal(9, 12)", "Decimal(39, 2)"))
def test_decimal_requires_success_of_existing_shared_rule(tmp_path, type_expr):
    item = probe.fixture("postgres")
    source = item["source"].replace("Decimal(9, 2)", type_expr)
    _, result = probe.build_case(tmp_path, source, item["contract"])
    assert result.status == "BLOCKED" and any(
        b.code == "PIE-B1004" for b in result.blockers
    )


def test_decimal_alias_uses_exact_existing_terminal(tmp_path):
    item = probe.fixture("postgres")
    source = "type Money = Decimal(9, 2)\n" + item["source"].replace(
        "money: Decimal(9, 2)", "money: Money"
    )
    _, result = probe.build_case(tmp_path, source, item["contract"])
    assert result.status == "VERIFIED"
    assert probe.decode_public(serialize_project_sql_emission(result))["columns"][3][
        "logical_type"
    ]["parameters"] == {"precision": 9, "scale": 2}


def test_actual_negative_target_evidence_is_not_erased(built):
    from pietto.semantic.capability_facts import (
        CapabilityFact,
        CapabilityKey,
        CapabilityDomain,
        CapabilitySupport,
        CapabilityDisposition,
        CapabilityDispositionKind,
        CapabilityEvidence,
        CapabilityEvidenceSource,
    )
    from pietto.semantic.capability_profiles import (
        CapabilityProfileTarget,
        CapabilityProfileTargetKind,
        CapabilityProfileIdentity,
        CapabilityProfileReference,
        CapabilityProfileSchemaVersion,
        StaticCapabilityProfile,
        CapabilityProfileKind,
        CapabilityProfileFactOccurrence,
    )
    from pietto._project.project_sql_plan_target_assessment import (
        prepare_project_sql_target_request,
    )

    target = CapabilityProfileTarget(
        CapabilityProfileTargetKind.DATABASE, "postgresql", "18.6"
    )
    reference = CapabilityProfileReference(
        CapabilityProfileIdentity("fixture", "denial"), "1"
    )
    fact = CapabilityFact(
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "Int",
            "catalog_membership",
            context="builtin_registry",
        ),
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDisposition(CapabilityDispositionKind.NONE),
        (
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST, "fixture", "explicit-denial"
            ),
        ),
    )
    profile = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        reference,
        target,
        CapabilityProfileKind.BASE,
        (),
        (CapabilityProfileFactOccurrence(reference, 0, fact),),
    )
    item, checked, _ = built["postgres", "G_emission_table_bag"]
    request = prepare_project_sql_target_request(target, base=profile)
    result = emit_project_sql(
        checked, item["contract"].encode(), target_request=request
    )
    assert result.status == "BLOCKED" and any(
        b.code == "PIE-B1006" for b in result.blockers
    )
    assert any(
        b["reason"] == "UNFULFILLED_REQUIREMENT"
        for b in probe.decode_public(serialize_project_sql_emission(result))["blockers"]
    )


def test_old_artifact_rejects_coherent_sidecar_and_sql_change(built):
    _, _, outcome = built["postgres", "G_emission_table_bag"]
    artifact = outcome.artifact
    assert artifact is not None
    original = artifact.ast.scan.realization
    changed = graft(original, name="changed")
    request = graft(artifact.request, sources=(changed,))
    assert not verify_project_sql_emission(artifact, request).verified


def test_resource_hard_limits_cannot_be_raised(built):
    from pietto._project.project_sql_emission_ast import resource_limits

    item, checked, _ = built["postgres", "G_emission_table_bag"]
    document = json.loads(item["contract"])
    document["environment"].append(
        {
            "key": "resource_limits",
            "scope": "statement",
            "value": {
                "sql_bytes": 999999999,
                "artifact_bytes": 999999999,
                "nodes": 999999999,
                "parameters": 999999999,
                "columns": 999999999,
            },
        }
    )
    request = prepare_project_sql_emission(checked, probe.encoded(document))
    assert resource_limits(request) == {
        "sql_bytes": 8 * 1024 * 1024,
        "artifact_bytes": 16 * 1024 * 1024,
        "nodes": 32768,
        "parameters": 32768,
        "columns": 1664,
    }
    assert (
        emit_project_sql(checked, b" " * (1024 * 1024 + 1)).status == "INPUT_REJECTED"
    )
    assert (
        emit_project_sql(checked, b"[" * 129 + b"0" + b"]" * 129).status
        == "INPUT_REJECTED"
    )


@pytest.mark.parametrize("mode", ("cross_source", "unused_conflict"))
def test_all_premise_scopes_are_bound_and_coherent(tmp_path, mode):
    item = probe.fixture("postgres")
    source = item["source"] + '\nsource unused: Row is mysql.table("unrelated")\n'
    document = json.loads(item["contract"])
    unused = deepcopy(document["sources"][0])
    unused["selector"]["name"] = "unused"
    document["sources"].append(unused)
    checked, result = probe.build_case(tmp_path, source, probe.encoded(document))
    assert result.status == "VERIFIED"
    if mode == "cross_source":
        assert result.artifact is not None
        site = result.artifact.request.plan.expression_sites[0]
        document["environment"].append(
            {
                "key": "encoding",
                "scope": {
                    "kind": "expression",
                    "source": unused["selector"],
                    "site": {
                        "kind": site.ref.kind.value,
                        "position": site.ref.position,
                    },
                    "context": {
                        "kind": site.block.kind.value,
                        "position": site.block.position,
                    },
                },
                "value": "UTF8",
            }
        )
    else:
        unused["premises"].append(
            {"key": "row_domain_matches", "scope": "source", "value": False}
        )
    result = emit_project_sql(checked, probe.encoded(document))
    assert result.artifact is None
    assert result.status == ("INPUT_REJECTED" if mode == "cross_source" else "BLOCKED")
    if mode == "unused_conflict":
        assert [b.code for b in result.blockers] == ["PIE-B1005"]


def test_whole_project_error_and_malformed_input_both_remain_visible(tmp_path):
    item = probe.fixture("postgres")
    source = (
        item["source"]
        + "\nquery broken:\n    from rows\n    select:\n        missing\n"
    )
    checked, result = probe.build_case(tmp_path, source, item["contract"])
    assert result.status == "BLOCKED" and result.artifact is None
    assert result.diagnostics is checked.completed.diagnostics
    assert any(d.severity.value == "error" for d in result.diagnostics)
    malformed = emit_project_sql(checked, b'{"wrong":0}')
    assert (
        malformed.status == "INPUT_REJECTED"
        and malformed.diagnostics is result.diagnostics
    )


def test_malformed_root_is_handled_without_traceback(built):
    item, checked, _ = built["postgres", "G_emission_table_bag"]
    result = emit_project_sql(graft(checked, completed=None), item["contract"].encode())
    assert (
        probe.decode_public(serialize_project_sql_emission(result))["status"]
        == "INPUT_REJECTED"
    )


@pytest.mark.parametrize(
    "change",
    (
        "nested_extra",
        "logical_storage",
        "port_position",
        "range_owner",
        "bool_storage_precision",
    ),
)
def test_public_nested_correspondence_rejections(built, change):
    _, _, outcome = built["postgres", "G_emission_table_bag"]
    document = json.loads(serialize_project_sql_emission(outcome))
    if change == "nested_extra":
        document["request"]["contract"]["sources"][0]["fields"][0]["extra"] = 1
    elif change == "logical_storage":
        document["columns"][0]["logical_type"]["name"] = "Float"
    elif change == "port_position":
        document["columns"][0]["correspondence"]["input_port"]["position"] = 100
    elif change == "range_owner":
        document["ranges"][1]["subject"]["position"] = 100
    else:
        document["request"]["contract"]["sources"][0]["fields"][3]["representation"][
            "storage"
        ]["precision"] = True
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


def test_json_escaping_preserves_sql_byte_ranges_and_decoder_independence(
    built, monkeypatch
):
    import pietto._project.project_sql_emission as emission

    _, _, outcome = built["postgres", "G_emission_table_bag"]
    public = serialize_project_sql_emission(outcome)
    escaped = json.dumps(json.loads(public), ensure_ascii=True).encode()

    def forbidden(*args, **kwargs):
        raise AssertionError("production called by data-only decoder")

    monkeypatch.setattr(emission, "serialize_project_sql_emission", forbidden)
    monkeypatch.setattr(emission, "verify_project_sql_emission", forbidden)
    decoded = probe.decode_public(escaped)
    assert decoded == json.loads(public)
    assert decoded["sql"].encode() == outcome.artifact.rendered.sql


def test_zero_parameter_capability_allows_empty_bind_envelope(built):
    item, checked, _ = built["postgres", "H_emission_query_bag"]
    document = json.loads(item["contract"])
    document["environment"].append(
        {"key": "resource_limits", "scope": "statement", "value": {"parameters": 0}}
    )
    result = emit_project_sql(checked, probe.encoded(document))
    assert result.status == "VERIFIED"
    assert (
        probe.decode_public(serialize_project_sql_emission(result))["parameter_uses"]
        == []
    )


def test_repeated_source_field_has_distinct_positional_exports(tmp_path):
    item = probe.fixture("postgres")
    source = item["source"].replace(
        "        record_id = id", "        record_id = id\n        second_id = id"
    )
    _, result = probe.build_case(tmp_path, source, item["contract"])
    assert result.status == "VERIFIED"
    public = probe.decode_public(serialize_project_sql_emission(result))
    assert [c["correspondence"]["field"] for c in public["columns"]] == [
        2,
        0,
        0,
        1,
        3,
        4,
    ]
    assert (
        public["columns"][1]["correspondence"]["input_port"]
        == public["columns"][2]["correspondence"]["input_port"]
    )
    assert (
        public["columns"][1]["correspondence"]["export"]
        != public["columns"][2]["correspondence"]["export"]
    )


def test_nonempty_binding_requires_explicit_native_protocol_evidence(tmp_path):
    item = probe.fixture("postgres")
    source = item["source"]
    source = source.replace("        ratio\n", "        ratio\n        marker = 1\n")
    checked, result = probe.build_case(
        tmp_path, source, item["contract"], "bind_safe_literals"
    )
    assert result.status == "BLOCKED" and result.artifact is None
    assert any(
        b.code == "PIE-B1004" and b.detail == "parameter_protocol_declaration_missing"
        for b in result.blockers
    )
    assert checked.envelope is not None and checked.envelope.values


@pytest.mark.parametrize(
    "key,value", ((7, "UTF8"), ("made_up", True), ("client_encoding", {}))
)
def test_public_premise_types_are_closed(built, key, value):
    _, _, outcome = built["postgres", "G_emission_table_bag"]
    document = json.loads(serialize_project_sql_emission(outcome))
    document["request"]["contract"]["environment"][0] = {
        "key": key,
        "scope": "statement",
        "value": value,
    }
    document["target"]["environment"] = document["request"]["contract"]["environment"]
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


def test_current_emission_variant_manifest_is_complete():
    assert probe.VARIANTS == {
        # Slice9 windows: the admitted R14 families, R15 frames and named
        # windows, R17 selected/hidden QUALIFY, and the exact refusal set.
        "A_window_ranking": ("peers",),
        "A_window_distribution": ("spread",),
        "A_window_navigation": ("offsets",),
        "A_window_frame": ("rows", "range"),
        "A_window_groups": ("exclude",),
        "A_window_named": ("shared",),
        "A_window_qualify": ("selected", "hidden"),
        "V_window_blocked": ("ignore_nulls", "from_last", "offset_range_keys"),
        "G_emission_table_bag": ("bag",),
        "H_emission_query_bag": ("bag",),
        "I_emission_table_empty": ("empty",),
        "J_emission_query_empty": ("empty",),
        "K_emission_rejected": ("duplicate_selector", "ordinal_bool", "stale_selector"),
        "L_emission_blocked": (
            "missing_source",
            "bool_domain",
            "decimal_mismatch",
            "timestamp_meaning",
            "uuid_meaning",
            "where_later",
        ),
        "M_named_chain": ("table_bag", "query_bag", "empty", "long_intermediate"),
        "N_imported_chain": ("bag", "empty"),
        "O_named_later": (
            "self_join",
            "union_dag",
            "two_facades",
            "order_ordinary",
            "order_rebound",
            "order_completed",
            "producer_filter",
        ),
        "P_native_identifiers": (
            "preserve",
            "bind",
            "plain_preserve",
            "plain_bind",
            "named_preserve",
            "named_bind",
            "empty_preserve",
            "empty_bind",
        ),
        "R_fixed_direct": (
            "table_preserve",
            "table_bind",
            "query_preserve",
            "query_bind",
            "empty_preserve",
            "empty_bind",
        ),
        "S_fixed_named": (
            "named_preserve",
            "named_bind",
            "imported_preserve",
            "imported_bind",
            "empty_preserve",
            "empty_bind",
        ),
        # Slice6 row stages: successful direct/named pipelines and the finite
        # boundary set that keeps no usable partial SQL.
        "T_row_direct": (
            "table_preserve",
            "query_bind",
            "empty_preserve",
            "truth_table",
        ),
        "U_row_named": ("named_preserve", "imported_bind", "empty_preserve"),
        "V_row_blocked": (
            "float_arithmetic",
            "float_comparison",
            "bool_comparison",
            "int_overflow",
            "unary_overflow",
            "modulo",
            "between",
            "match_join",
        ),
        # Slice7 JOIN/EXISTS: the seven admitted kinds inside their own approved
        # domains, the outer value transport, and the per-target restricted FULL.
        "W_join_shapes": ("cross", "inner", "semi", "anti"),
        "W_join_values": ("left_marker", "right_accumulated", "via_refined"),
        "V_join_full": ("restricted",),
        # Slice8 aggregation: GLOBAL and GROUPED results, satisfying, the
        # reviewed comparison domains, composition, membership and the exact
        # first-version non-support set.
        "X_aggregate_global": ("bag", "empty", "all_null", "where_false"),
        "X_aggregate_grouped": ("hidden", "visible", "empty"),
        "Y_aggregate_constant": ("grouped", "empty"),
        "Y_aggregate_satisfying": ("retained", "let_reference", "bind", "before_input"),
        "Y_aggregate_domains": ("bool_key", "text_key", "decimal_key"),
        "Z_aggregate_composition": (
            "named",
            "imported",
            "let_where",
            "downstream_filter",
            "source_keys",
        ),
        "Z_aggregate_joined": (
            "inner_fanout",
            "left_nullable",
            "right_accumulated",
            "full_restricted",
        ),
        "Z_aggregate_membership": (
            "semi_global",
            "anti_global",
            "semi_grouped",
            "anti_grouped",
            "filtered_global",
            "satisfying_right",
        ),
        "Z_aggregate_transport": ("outer_null",),
        "V_aggregate_blocked": (
            "sum_direct",
            "avg_direct",
            "sum_hidden_right",
            "float_key",
            "bool_domain_key",
            "decimal_parameter_key",
        ),
        # Slice10 result boundaries: visible DISTINCT, the three ORDER carriers
        # and static LIMIT, their sharing/membership witnesses, the Slice9
        # composition and the exact refusal set.
        "O_result_distinct": ("visible_int", "null_duplicates", "hidden_group"),
        "O_result_order": (
            "ordinary_desc",
            "nullable_key",
            "constant_key",
            "helper_hidden",
        ),
        "O_result_limit": (
            "positive",
            "zero",
            "inner_then_filter",
            "filter_then_limit",
        ),
        "O_result_sharing": ("order_limit_self_join",),
        "O_result_membership": (
            "semi_limit1",
            "anti_limit1",
            "semi_limit0",
            "anti_limit0",
        ),
        "O_result_window": (
            "qualify_distinct",
            "selected_order",
            "qualify_order_limit",
        ),
        "V_result_blocked": ("hidden_strict_fd", "float_distinct", "order_expression"),
        # Slice11 SET forms: the C17 base pair, multiplicity, positions, domains,
        # nesting, operand-local boundaries, producers, membership, literals and
        # the exact refusal set.
        "S_set_forms": (
            "union_all",
            "union_distinct",
            "intersect_all",
            "intersect_distinct",
            "except_all",
            "except_distinct",
        ),
        "S_set_multiplicity": (
            "intersect_all",
            "intersect_distinct",
            "empty_left",
            "empty_right",
        ),
        "S_set_positions": (
            "two_column_intersect_distinct",
            "two_column_except_all",
            "renamed_labels_union_all",
        ),
        "S_set_domains": (
            "text_union_distinct",
            "decimal_intersect_all",
            "big_int_except_all",
            "bool_union_distinct",
            "float_union_all",
        ),
        "S_set_nesting": (
            "left_fold_except",
            "right_nested_except",
            "mixed_union_except",
        ),
        "S_set_boundaries": (
            "ordered_operands",
            "limit_zero_operand",
            "distinct_operand",
            "outer_consumer",
        ),
        "S_set_producers": (
            "grouped_union",
            "global_empty_union",
            "satisfying_union",
            "window_union_distinct",
            "set_to_window",
        ),
        "S_set_membership": (
            "semi_except",
            "anti_except",
            "semi_intersect",
            "anti_intersect",
        ),
        "S_set_literals": ("preserve", "bind"),
        "V_set_blocked": (
            "physical_mismatch",
            "float_intersect_all",
            "arity_mismatch",
            "type_mismatch",
        ),
    }
    for target in ("postgres", "mysql"):
        inputs = probe.generation_inputs(target)
        assert len(inputs) == 181
        assert (
            sum(
                item["id"]
                in {
                    "G_emission_table_bag",
                    "H_emission_query_bag",
                    "I_emission_table_empty",
                    "J_emission_query_empty",
                    "K_emission_rejected",
                    "L_emission_blocked",
                }
                for item in inputs
            )
            == 13
        )


def test_multiple_later_scalar_projections_keep_each_blocker(tmp_path):
    item = probe.fixture("postgres")
    # Slice6 admits signed-Int arithmetic, so this case keeps its original purpose
    # with `between`, which is still a later-slice scalar projection.
    source = item["source"].replace(
        "        ratio\n",
        "        ratio\n"
        "        first = id between 0 and 10\n"
        "        second = id between 1 and 20\n",
    )
    _, result = probe.build_case(tmp_path, source, item["contract"])
    blockers = [
        b
        for b in result.blockers
        if b.detail == "scalar_projection_requires_later_slice"
    ]
    assert len(blockers) == 2 and blockers[0].subject is not blockers[1].subject
    public = probe.decode_public(serialize_project_sql_emission(result))
    assert [
        b["location"]["line"]
        for b in public["blockers"]
        if b["subject"]["detail"] == "scalar_projection_requires_later_slice"
    ] == [16, 17]


def test_expression_premise_binds_exact_source_port(built):
    item, checked, outcome = built["postgres", "G_emission_table_bag"]
    assert outcome.artifact is not None
    site = outcome.artifact.request.plan.expression_sites[0]
    document = json.loads(item["contract"])
    document["environment"].append(
        {
            "key": "encoding",
            "scope": {
                "kind": "expression",
                "source": document["sources"][0]["selector"],
                "site": {"kind": site.ref.kind.value, "position": site.ref.position},
                "context": {
                    "kind": site.block.kind.value,
                    "position": site.block.position,
                },
            },
            "value": "UTF8",
        }
    )
    result = emit_project_sql(checked, probe.encoded(document))
    assert result.status == "VERIFIED"
    assert (
        probe.decode_public(serialize_project_sql_emission(result))["status"]
        == "VERIFIED"
    )


def test_public_artifact_limit_blocks_runtime_success_too(built):
    item, checked, _ = built["postgres", "G_emission_table_bag"]
    document = json.loads(item["contract"])
    document["environment"].append(
        {"key": "resource_limits", "scope": "statement", "value": {"artifact_bytes": 1}}
    )
    result = emit_project_sql(checked, probe.encoded(document))
    assert result.status == "BLOCKED" and result.artifact is None
    assert [b.code for b in result.blockers] == ["PIE-B1007"]
    assert (
        probe.decode_public(serialize_project_sql_emission(result))["status"]
        == "BLOCKED"
    )
