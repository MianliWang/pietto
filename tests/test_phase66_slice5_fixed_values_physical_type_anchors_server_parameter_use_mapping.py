"""Original leaf/sign values, independent bytes/public maps and narrow scope."""

from copy import copy, deepcopy
from dataclasses import replace
import hashlib
import json
from typing import cast

import pytest

import _pietto_phase66_sql_emission_probe as probe
import _pietto_target_conformance as facility
import _pietto_target_conformance_observation as observation
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_plan_expressions as expressions
from pietto._project.project_sql_emission import (
    emit_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import SQLLiteralColumn
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)


# Field-only counterparts of the fixed documents: the same field obligations
# without a literal anywhere in the public grammar.
FIELD_ONLY = (
    ("P_native_identifiers", "preserve"),
    ("P_native_identifiers", "bind"),
    ("P_native_identifiers", "named_preserve"),
    ("G_emission_table_bag", "bag"),
    ("N_imported_chain", "bag"),
)
MIXED = (
    ("R_fixed_direct", "query_preserve"),
    ("R_fixed_direct", "query_bind"),
    ("S_fixed_named", "named_preserve"),
    ("S_fixed_named", "imported_bind"),
)
# Approved-contract incompatibility per physical source storage; no production
# type resolver decides whether an independent consumer accepts a document.
INCOMPATIBLE_DOMAIN = {
    "pg_int8": {"kind": "finite_float", "format": "binary64"},
    "my_bigint": {"kind": "finite_float", "format": "binary64"},
    "pg_bool": {"kind": "int_range", "min": "0", "max": "2"},
    "my_bool01": {"kind": "int_range", "min": "0", "max": "2"},
    "pg_text": {"kind": "bool01"},
    "my_varchar": {"kind": "bool01"},
    "pg_numeric": {"kind": "int_range", "min": "0", "max": "9"},
    "my_decimal": {"kind": "int_range", "min": "0", "max": "9"},
    "pg_float8": {"kind": "int_range", "min": "0", "max": "1"},
    "my_double": {"kind": "int_range", "min": "0", "max": "1"},
}


@pytest.fixture(scope="module")
def products(tmp_path_factory):
    result = {}
    selected = [
        (case, variant)
        for case in ("R_fixed_direct", "S_fixed_named")
        for variant in probe.VARIANTS[case]
    ]
    for target in ("postgres", "mysql"):
        for case, variant in [*selected, *FIELD_ONLY]:
            item = probe.fixture(target, case, variant)
            checked, outcome = probe.build_case(
                tmp_path_factory.mktemp("fixed"),
                item["source"],
                item["contract"],
                item["policy"],
            )
            result[target, case, variant] = checked, outcome
    return result


def public(products, target, case, variant):
    _, outcome = products[target, case, variant]
    return json.loads(serialize_project_sql_emission(outcome))


def retained_fields(document):
    """The selected scan closure keeps every field, projected or not."""
    return document["request"]["contract"]["sources"][0]["fields"]


def field_outputs(document):
    """Output ordinals per source field ordinal; a literal column owns no field."""
    result = {}
    for index, column in enumerate(document["columns"]):
        ordinal = column["correspondence"].get("field")
        if ordinal is not None:
            result.setdefault(ordinal, []).append(index)
    return result


def corrupted(document, ordinal, how, domain):
    document = deepcopy(document)
    if how != "output":
        retained_fields(document)[ordinal]["representation"]["domain"] = deepcopy(
            domain
        )
    if how != "source":
        for index in field_outputs(document).get(ordinal, ()):
            document["columns"][index]["representation"]["domain"] = deepcopy(domain)
    return document


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    [
        (case, variant)
        for case in ("R_fixed_direct", "S_fixed_named")
        for variant in probe.VARIANTS[case]
    ],
)
def test_actual_source_public_vertical(products, target, case, variant):
    checked, outcome = products[target, case, variant]
    assert checked.verified
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    named = case == "S_fixed_named"
    count = 5 if named else 18
    bound = variant.endswith("bind")
    assert (
        len(document["fixed_values"])
        == len(document["parameter_uses"])
        == (count if bound else 0)
    )
    assert len(probe.decoded_arguments(document)) == (count if bound else 0)
    if bound:
        assert all(
            a is b
            for a, b in zip(artifact.fixed_values, checked.envelope.values, strict=True)
        )
        assert [use["server_index"] for use in document["parameter_uses"]] == list(
            range(1, count + 1)
        )
    assert len(document["columns"]) == (7 if named else 20)
    assert document["columns"][0]["correspondence"]["field"] == 0
    zero = next(
        c
        for c in document["columns"]
        if c["label"] == ("zero" if named else "negative_zero")
    )
    assert "source_port" not in zero["correspondence"]
    assert zero["logical_type"]["name"] == "Float" and zero["nullable"] is False
    if bound:
        slot = zero["correspondence"]["literal_origin"]["slot"]
        assert document["fixed_values"][slot]["value"] == "0x0.0p+0"
    if named:
        first, again = document["columns"][2:4]
        assert (
            first["correspondence"]["literal_origin"]
            == again["correspondence"]["literal_origin"]
        )
        assert (
            first["correspondence"]["input_port"]
            != again["correspondence"]["input_port"]
        )
        assert len(artifact.ast.ctes) == 2
        assert len(artifact.ast.ctes[0].body.columns) == 5  # unused true remains.


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_component_zero_one_many_mapping_does_not_claim_query_duplication(
    products, target
):
    checked, _ = products[target, "R_fixed_direct", "query_bind"]
    leaves = [
        e
        for e in checked.plan.expressions
        if type(e) is expressions.ProjectSQLBoundLiteral and e.expression.value == 17
    ]
    assert len(leaves) == 2 and leaves[0].use.slot is not leaves[1].use.slot
    physical = "pg_int8" if target == "postgres" else "my_signed_int"
    assert parameters.allocate_uses(target, (), 0) == ()
    one = parameters.allocate_uses(target, ((leaves[0], physical),), 1)
    assert one[0].server_index == 1 and one[0].slot is leaves[0].use.slot
    repeated = parameters.allocate_uses(target, ((leaves[0], physical),) * 3, 3)
    assert [use.server_index for use in repeated] == (
        [1, 1, 1] if target == "postgres" else [1, 2, 3]
    )
    distinct = parameters.allocate_uses(
        target, tuple((leaf, physical) for leaf in leaves), 2
    )
    assert [use.server_index for use in distinct] == [1, 2]
    with pytest.raises(ValueError, match="incompatible_slot_context"):
        parameters.allocate_uses(
            target, ((leaves[0], physical), (leaves[0], "other_context")), 2
        )
    with pytest.raises(ValueError, match="limit"):
        parameters.allocate_uses(target, ((leaves[0], physical),) * 3, 2)
    assert (
        len(parameters.allocate_uses(target, ((leaves[0], physical),) * 32768, 32768))
        == 32768
    )
    with pytest.raises(ValueError, match="limit"):
        parameters.allocate_uses(target, ((leaves[0], physical),) * 32769, 32768)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "source_value,code",
    [
        ("-9223372036854775808", "PIE-B1002"),  # positive leaf cannot fit signed64
        ("9223372036854775808", "PIE-B1002"),
        # Slice6 admits signed-Int +,-,* and field signs, so these boundaries keep
        # their purpose with an operator and a node type it still does not admit.
        ("id % 2", "PIE-B1003"),
        ("id between 0 and 1", "PIE-B1003"),
    ],
)
def test_complete_shape_and_representation_boundaries(
    tmp_path, target, source_value, code
):
    item = probe.native_fixture(target, "preserve")
    source = item["source"].replace("id = id", "value = " + source_value)
    checked, outcome = probe.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED" and document["artifact"] is None
    assert code in [b["code"] for b in document["blockers"]]
    assert "sql" not in document and "fixed_values" not in document


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_untyped_null_retains_the_original_unavailable_root(tmp_path, target):
    item = probe.native_fixture(target, "preserve")
    checked, outcome = probe.build_case(
        tmp_path,
        item["source"].replace("id = id", "value = null"),
        item["contract"],
        item["policy"],
    )
    assert not checked.verified and checked.envelope is None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED" and document["artifact"] is None
    assert [d["code"] for d in document["diagnostics"]] == ["PIE-S2333"]
    assert all(b["code"] == "PIE-B1003" for b in document["blockers"])


@pytest.mark.parametrize("spelling", ("inf", "-inf", "nan", "0x1p+1024"))
def test_nonfinite_fixed_payloads_fail_without_inventing_source_syntax(
    products, spelling
):
    _, outcome = products["postgres", "R_fixed_direct", "query_bind"]
    document = json.loads(serialize_project_sql_emission(outcome))
    value = next(v for v in document["fixed_values"] if v["tag"] == "Float")
    value["value"] = spelling
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))
    assert not parameters.value_valid("Float", float("inf"), "postgres")
    assert not parameters.value_valid("Float", float("nan"), "mysql")


@pytest.mark.parametrize(
    "mutation",
    (
        "slot_swap",
        "slot_merge",
        "wrong_index",
        "bool_index",
        "missing_use",
        "missing_values",
        "enclosure",
        "placeholder_range",
        "literal_origin",
        "dropped_anchor",
    ),
)
def test_public_parameter_and_provenance_corruptions(products, mutation):
    _, outcome = products["postgres", "R_fixed_direct", "query_bind"]
    document = json.loads(serialize_project_sql_emission(outcome))
    if mutation == "slot_swap":
        document["fixed_values"][0], document["fixed_values"][1] = (
            document["fixed_values"][1],
            document["fixed_values"][0],
        )
    elif mutation == "slot_merge":
        document["parameter_uses"][1]["slot"] = 0
    elif mutation == "wrong_index":
        document["parameter_uses"][0]["server_index"] = 2
    elif mutation == "bool_index":
        document["parameter_uses"][0]["use"] = False
    elif mutation == "missing_use":
        document["parameter_uses"].pop()
    elif mutation == "missing_values":
        document["fixed_values"].clear()
    elif mutation == "enclosure":
        document["ranges"][-1]["end"] -= 1
    elif mutation == "placeholder_range":
        document["parameter_uses"][0]["range"]["start"] += 1
    elif mutation == "literal_origin":
        document["columns"][2]["correspondence"] = document["columns"][0][
            "correspondence"
        ]
    else:
        document["requirements"] = [
            r for r in document["requirements"] if r["kind"] != "type_anchor"
        ]
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("mutation", ("sign", "float", "text", "tag", "unknown"))
def test_preserve_tokens_bind_to_values_and_sign_metadata(products, mutation):
    _, outcome = products["postgres", "R_fixed_direct", "query_preserve"]
    document = json.loads(serialize_project_sql_emission(outcome))
    if mutation == "sign":
        document["sql"] = document["sql"].replace("(-CAST(", "(+CAST(", 1)
    elif mutation == "float":
        document["sql"] = document["sql"].replace("'1.0'", "'2.0'", 1)
    elif mutation == "text":
        document["sql"] = document["sql"].replace("\\141", "\\142", 1)
    else:
        evidence = next(
            r["evidence"][0] for r in document["requirements"] if r["kind"] == "literal"
        )
        if mutation == "tag":
            evidence["tag"] = "Int"
        else:
            evidence["extra"] = None
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


def test_runtime_origin_and_equal_slot_identity(products):
    _, outcome = products["postgres", "R_fixed_direct", "query_bind"]
    artifact = outcome.artifact
    assert artifact is not None
    columns = artifact.ast.columns
    first = columns[2]
    assert type(first) is SQLLiteralColumn and first.value is not None
    changed = replace(first, origin=replace(first.origin, export=columns[3].export))
    corrupt = replace(
        artifact,
        ast=replace(artifact.ast, columns=(*columns[:2], changed, *columns[3:])),
    )
    assert not verify_project_sql_emission(corrupt, artifact.request).verified
    value = parameters.value_nodes(first.value)[-1]
    assert type(value) is parameters.SQLParameter
    foreign = copy(value.fixed)
    bad = replace(first.value, operand=replace(value, fixed=foreign))
    changed = replace(first, value=bad, origin=replace(first.origin, value=bad))
    corrupt = replace(
        artifact,
        ast=replace(artifact.ast, columns=(*columns[:2], changed, *columns[3:])),
    )
    assert not verify_project_sql_emission(corrupt, artifact.request).verified


def test_verifiers_and_serializer_do_not_build_values_or_sql(products, monkeypatch):
    _, outcome = products["mysql", "S_fixed_named", "imported_bind"]

    def forbidden(*args, **kwargs):
        raise AssertionError("builder called by verifier")

    for name in ("build_value", "allocate_uses", "literal_token", "anchor_suffix"):
        monkeypatch.setattr(parameters, name, forbidden)
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    probe.decode_public(serialize_project_sql_emission(outcome))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", [*FIELD_ONLY, *MIXED])
@pytest.mark.parametrize("how", ("source", "output", "coordinated"))
def test_an_added_literal_never_weakens_an_existing_field(
    products, target, case, variant, how
):
    document = public(products, target, case, variant)
    assert probe.decode_public(probe.encoded(document))["status"] == "VERIFIED"
    outputs, fields = field_outputs(document), retained_fields(document)
    reached = 0
    for ordinal, field in enumerate(fields):
        if how != "source" and ordinal not in outputs:
            continue  # An omitted field owns no output column to corrupt.
        domain = INCOMPATIBLE_DOMAIN[field["representation"]["storage"]["kind"]]
        with pytest.raises(ValueError):
            probe.decode_public(
                probe.encoded(corrupted(document, ordinal, how, domain))
            )
        reached += 1
    assert reached == (len(fields) if how == "source" else len(outputs))
    assert bool(set(range(len(fields))) - set(outputs)) == (case[0] in "PRS")


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_every_admitted_type_family_keeps_its_own_declared_domain(products, target):
    document = public(products, target, "G_emission_table_bag", "bag")
    assert {c["logical_type"]["name"] for c in document["columns"]} == {
        "Int",
        "Bool",
        "Text",
        "Decimal",
        "Float",
    }
    for ordinal, field in enumerate(retained_fields(document)):
        domain = INCOMPATIBLE_DOMAIN[field["representation"]["storage"]["kind"]]
        with pytest.raises(ValueError):
            probe.decode_public(
                probe.encoded(corrupted(document, ordinal, "coordinated", domain))
            )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "change",
    (
        "int_above_storage",
        "int_below_storage",
        "int_empty_range",
        "int_noncanonical",
        "text_encoding",
        "text_collation",
        "text_padding",
        "text_no_characters",
        "decimal_precision",
        "decimal_scale_above_precision",
        "decimal_storage_disagreement",
        "float_format",
        "foreign_family_storage",
        "expression_anchor_storage",
        "null_posture",
        "null_disagreement",
    ),
)
def test_declared_constraints_decide_more_than_recognized_tags(
    products, target, change
):
    document = public(products, target, "G_emission_table_bag", "bag")
    ordinal = {
        "int_above_storage": 0,
        "int_below_storage": 0,
        "int_empty_range": 0,
        "int_noncanonical": 0,
        "text_encoding": 2,
        "text_collation": 2,
        "text_padding": 2,
        "text_no_characters": 2,
        "decimal_precision": 3,
        "decimal_scale_above_precision": 3,
        "decimal_storage_disagreement": 3,
        "float_format": 4,
        "foreign_family_storage": 0,
        "expression_anchor_storage": 0,
        "null_posture": 1,
        "null_disagreement": 1,
    }[change]
    postgres = target == "postgres"
    representation = retained_fields(document)[ordinal]["representation"]
    domain, storage = representation["domain"], representation["storage"]
    if change == "int_above_storage":
        domain["max"] = "9223372036854775808"
    elif change == "int_below_storage":
        domain["min"] = "-9223372036854775809"
    elif change == "int_empty_range":
        domain["min"], domain["max"] = "1", "0"
    elif change == "int_noncanonical":
        domain["max"] = "+9007199254740993"
    elif change == "text_encoding":
        domain["encoding"] = "LATIN1"
    elif change == "text_collation":
        domain["collation"] = "POSIX" if postgres else "utf8mb4_general_ci"
    elif change == "text_padding":
        domain["padding"] = "PAD SPACE"
    elif change == "text_no_characters":
        domain["max_characters"] = 0
    elif change == "decimal_precision":
        domain["precision"] = storage["precision"] = 66
    elif change == "decimal_scale_above_precision":
        domain["scale"] = storage["scale"] = 31
    elif change == "decimal_storage_disagreement":
        domain["scale"] = 3  # Storage keeps scale 2: exactness, not a tag match.
    elif change == "float_format":
        domain["format"] = "binary32"
    elif change == "foreign_family_storage":
        storage["kind"] = "my_bigint" if postgres else "pg_int8"
    elif change == "expression_anchor_storage":
        # A generated literal anchor is never an accepted physical source tag.
        storage["kind"] = "my_signed_int"
    else:
        representation["nullable"] = "maybe"
    # Coordinate every copy, so only the declared constraint can reject.
    for index in field_outputs(document)[ordinal]:
        column = document["columns"][index]
        column["representation"] = deepcopy(representation)
        column["nullable"] = representation["nullable"]
        if column["logical_type"]["name"] == "Decimal":
            column["logical_type"]["parameters"] = {
                key: domain[key] for key in ("precision", "scale")
            }
        if change == "null_disagreement":
            column["representation"]["nullable"] = not representation["nullable"]
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "change", ("signed_bounds", "single_value", "unknown_null", "shorter_text")
)
def test_valid_field_declarations_are_still_accepted(products, target, change):
    document = public(products, target, "G_emission_table_bag", "bag")
    ordinal = {
        "signed_bounds": 0,
        "single_value": 0,
        "unknown_null": 1,
        "shorter_text": 2,
    }[change]
    representation = retained_fields(document)[ordinal]["representation"]
    domain = representation["domain"]
    if change == "signed_bounds":
        domain["min"], domain["max"] = "-9223372036854775808", "9223372036854775807"
    elif change == "single_value":
        domain["min"] = domain["max"] = "0"
    elif change == "unknown_null":
        representation["nullable"] = "unknown"
    else:
        domain["max_characters"] = 1
    for index in field_outputs(document)[ordinal]:
        column = document["columns"][index]
        column["representation"] = deepcopy(representation)
        column["nullable"] = representation["nullable"]
    assert probe.decode_public(probe.encoded(document))["status"] == "VERIFIED"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    (("G_emission_table_bag", "bag"), ("R_fixed_direct", "query_preserve")),
)
def test_unrelated_sources_keep_structure_without_selected_applicability(
    tmp_path, target, case, variant
):
    item = probe.fixture(target, case, variant)
    contract = json.loads(item["contract"])
    unused = deepcopy(contract["sources"][0])
    unused["selector"]["name"] = "unused"
    foreign = "my_smallint" if target == "postgres" else "pg_int2"
    unused["fields"][0]["representation"]["storage"]["kind"] = foreign
    contract["sources"].append(unused)
    other = "mysql" if target == "postgres" else "postgres"
    checked, outcome = probe.build_case(
        tmp_path,
        item["source"] + f'\nsource unused: Row is {other}.table("unrelated")\n',
        probe.encoded(contract),
        item["policy"],
    )
    assert checked.verified and outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED"
    sources = document["request"]["contract"]["sources"]
    assert sources[1]["fields"][0]["representation"]["storage"]["kind"] == foreign
    # The unrelated description still owes complete structure.
    broken = json.loads(serialize_project_sql_emission(outcome))
    broken["request"]["contract"]["sources"][1]["fields"][0]["ordinal"] = True
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(broken))


class SubmissionSpy:
    """Bounded offline consumer boundary; no driver, socket or server exists."""

    def __init__(self):
        self.submission_count = 0
        self.submitted: list[str] = []

    def capture(self, sql, parameters=(), **kwargs):
        self.submission_count += 1
        self.submitted.append(sql)
        return {"sql": sql, "parameters": parameters, "rows": []}


def emission_records(products, target, corrupt_variant=None):
    records = []
    for variant in probe.VARIANTS["R_fixed_direct"]:
        document = public(products, target, "R_fixed_direct", variant)
        if variant == corrupt_variant:
            storage = retained_fields(document)[0]["representation"]["storage"]["kind"]
            document = corrupted(
                document, 0, "coordinated", INCOMPATIBLE_DOMAIN[storage]
            )
        data = probe.encoded(document)
        records.append(
            {
                "id": "R_fixed_direct",
                "variant": variant,
                "public": data.decode(),
                "public_sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {"emission": {"records": records}}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_malformed_public_document_never_reaches_a_submission(products, target):
    spy = SubmissionSpy()
    seen = cast(observation.Observer, spy)
    accepted: dict = {"id": "R_fixed_direct", "observations": []}
    facility.execute_case(
        "R_fixed_direct",
        target,
        seen,
        seen,
        emission_records(products, target),
        accepted,
    )
    variants = probe.VARIANTS["R_fixed_direct"]
    assert spy.submission_count == len(variants)
    assert [
        v["submission_after"] - v["submission_before"] for v in accepted["variants"]
    ]
    assert all(
        v["submission_after"] - v["submission_before"] == 1
        for v in accepted["variants"]
    )
    blocked = SubmissionSpy()
    barred = cast(observation.Observer, blocked)
    rejected: dict = {"id": "R_fixed_direct", "observations": []}
    with pytest.raises(ValueError):
        facility.execute_case(
            "R_fixed_direct",
            target,
            barred,
            barred,
            emission_records(products, target, corrupt_variant=variants[0]),
            rejected,
        )
    assert blocked.submission_count == 0 and blocked.submitted == []
    assert rejected["observations"] == [] and rejected["variants"] == []


BOTH_GRAMMARS = (
    ("P_native_identifiers", "preserve"),
    ("G_emission_table_bag", "bag"),
    ("N_imported_chain", "bag"),
    ("R_fixed_direct", "query_preserve"),
    ("S_fixed_named", "imported_bind"),
)


def restate(document, key, value):
    """Environment premises are echoed twice; a public document states them once."""
    for block in (
        document["request"]["contract"]["environment"],
        document["target"]["environment"],
    ):
        for premise in block:
            if premise["key"] == key:
                premise["value"] = value


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", BOTH_GRAMMARS)
@pytest.mark.parametrize(
    "change",
    (
        "row_domain_false",
        "read_only_false",
        "operator_environment",
        "client_encoding",
        "scan_requirement",
    ),
)
def test_both_public_grammars_require_the_scan_premises(
    products, target, case, variant, change
):
    document = public(products, target, case, variant)
    premises = document["request"]["contract"]["sources"][0]["premises"]
    if change in {"row_domain_false", "read_only_false"}:
        key = (
            "row_domain_matches" if change == "row_domain_false" else "read_only_object"
        )
        next(p for p in premises if p["key"] == key)["value"] = False
    elif change == "operator_environment":
        restate(document, "operator_environment", "extensions_allowed")
    elif change == "client_encoding":
        restate(document, "client_encoding", "LATIN1")
    else:
        scan = next(
            r
            for r in document["requirements"]
            if r["denominator"] == "generated" and r["kind"] == "qualified_scan"
        )
        scan["premises"] = []
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", BOTH_GRAMMARS)
@pytest.mark.parametrize("kind", ("source_representation", "field_projection"))
def test_requirement_premise_domain_is_pinned_in_both_grammars(
    products, target, case, variant, kind
):
    document = public(products, target, case, variant)
    requirement = next(
        r
        for r in document["requirements"]
        if r["denominator"] == "generated" and r["kind"] == kind
    )
    assert requirement["premises"]
    requirement["premises"] = []
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


def expression_premise(contract, artifact, target, index=0):
    site = artifact.request.plan.expression_sites[index]
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
    return contract


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", BOTH_GRAMMARS[:4])
def test_expression_scoped_premises_bind_to_the_reading_field(
    products, target, case, variant
):
    checked, outcome = products[target, case, variant]
    assert outcome.artifact is not None
    item = probe.fixture(target, case, variant)
    contract = expression_premise(
        json.loads(item["contract"]), outcome.artifact, target
    )
    result = emit_project_sql(checked, probe.encoded(contract))
    assert result.status == "VERIFIED", serialize_project_sql_emission(result)
    data = serialize_project_sql_emission(result)
    document = probe.decode_public(data)
    assert document["status"] == "VERIFIED"
    position = len(contract["environment"]) - 1
    bound = [r for r in document["requirements"] if position in r["premises"]]
    assert {r["kind"] for r in bound} == {"source_representation", "field_projection"}
    # The premise belongs to the projections that actually read that field.
    for change in ("site", "context", "source"):
        moved = json.loads(data)
        for block in (
            moved["request"]["contract"]["environment"],
            moved["target"]["environment"],
        ):
            scope = block[position]["scope"]
            if change == "source":
                scope["source"] = dict(scope["source"], name="absent")
            else:
                scope[change]["position"] += 1
        with pytest.raises(ValueError):
            probe.decode_public(probe.encoded(moved))
