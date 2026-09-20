"""Real named chains, exact terminal scopes and independent public-byte checks."""

from copy import copy, deepcopy
from dataclasses import replace
import json
from time import perf_counter

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.project_sql_emission import (
    emit_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import SQLSelect
from pietto._project.project_sql_emission_scopes import (
    build_emission_layout,
    verify_emission_layout,
)
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)


def graft(value, **changes):
    changed = copy(value)
    for key, item in changes.items():
        object.__setattr__(changed, key, item)
    return changed


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    cache = {}

    def build(target="postgres", case="M_named_chain", variant="table_bag"):
        key = target, case, variant
        if key not in cache:
            item = probe.fixture(*key)
            checked, outcome = probe.build_case(
                tmp_path_factory.mktemp("named-emission"),
                item["source"],
                item["contract"],
                item["policy"],
            )
            cache[key] = item, checked, outcome
        return cache[key]

    return build


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    [
        ("M_named_chain", "table_bag"),
        ("M_named_chain", "query_bag"),
        ("M_named_chain", "empty"),
        ("M_named_chain", "long_intermediate"),
        ("N_imported_chain", "bag"),
        ("N_imported_chain", "empty"),
    ],
)
def test_real_named_public_vertical(built, target, case, variant):
    item, checked, outcome = built(target, case, variant)
    assert checked.verified
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["label"] for c in public["columns"]] == [
        "display_text",
        "record_id",
        "active",
        "amount",
        "ratio",
        "repeated",
    ]
    assert [c["logical_type"]["name"] for c in public["columns"]] == [
        "Text",
        "Int",
        "Bool",
        "Decimal",
        "Float",
        "Int",
    ]
    assert [c["correspondence"]["field"] for c in public["columns"]] == [
        2,
        0,
        1,
        3,
        4,
        0,
    ]
    assert public["columns"][2]["nullable"] is True
    assert public["columns"][3]["logical_type"]["parameters"] == {
        "precision": 9,
        "scale": 2,
    }
    assert public["fixed_values"] == public["parameter_uses"] == []
    assert public["request"]["literal_policy"] == item["policy"]
    assert [cte.symbol.name for cte in artifact.ast.ctes] == ["p0", "p1"]
    assert [len(cte.columns) for cte in artifact.ast.ctes] == [7, 6]
    assert len(artifact.ast.columns) == 6
    assert all(cte.body.ctes == () for cte in artifact.ast.ctes)
    assert artifact.rendered.sql == public["sql"].encode("utf-8")
    if variant == "long_intermediate":
        assert "intermediate_" not in public["sql"]
    if case == "N_imported_chain":
        assert {c["correspondence"]["source"]["module"] for c in public["columns"]} == {
            "a.pietto"
        }
        assert [s["module"] for s in public["request"]["sources"]] == [
            "a.pietto",
            "b.pietto",
            "main.pietto",
        ]
        imported = artifact.request.layout.uses[1].original
        assert imported.binding.local_name == "Alias"
        assert len(imported.origin_path.hops) == 2
        if variant == "bag":
            quote = '"' if target == "postgres" else "`"
            namespace = "public" if target == "postgres" else "phase66"
            assert f"FROM {quote}{namespace}{quote}.{quote}p0{quote}" in public["sql"]


def test_every_edge_uses_the_immediate_complete_terminal(built):
    _, checked, outcome = built()
    artifact = outcome.artifact
    assert artifact is not None
    layout = artifact.request.layout
    assert verify_emission_layout(layout, checked)
    assert [d.original.entry.owner.definition.name for d in layout.definitions] == [
        "rows",
        "first",
        "second",
        "result",
    ]
    assert [len(use.bindings) for use in layout.uses] == [5, 7, 6]
    for use in layout.uses:
        assert (
            use.original.origin_path
            is checked.plan.input_uses[use.original.ref.position].origin_path
        )
        for canonical, terminal, binding in zip(
            use.producer.original.exports,
            use.producer.terminals,
            use.bindings,
            strict=True,
        ):
            assert binding.canonical is canonical
            assert binding.terminal is terminal
            assert binding.input_port.producer_port is canonical.ref
    final = artifact.ast.columns
    assert final[1].source_port is final[5].source_port
    assert final[1].producer.canonical is not final[5].producer.canonical
    assert final[1].export is not final[5].export
    assert final[1].symbol is not final[5].symbol
    assert all(c.producer.terminal.ref.kind.value == "result_port" for c in final)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_direct_omission_keeps_full_original_input_requirements(tmp_path, target):
    item = probe.fixture(target)
    source = (
        item["source"].split("table result:", 1)[0]
        + "query result:\n    from rows\n    select:\n        id\n"
    )
    _, outcome = probe.build_case(tmp_path, source, item["contract"])
    assert outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert not document["sql"].startswith("WITH ")
    demands = [
        r
        for r in document["requirements"]
        if r["denominator"] == "original" and r["kind"] == "stage_value"
    ]
    assert len(demands) == 5
    document["requirements"].remove(demands[-1])
    for denominator in ("original", "generated"):
        for i, item in enumerate(
            r for r in document["requirements"] if r["denominator"] == denominator
        ):
            item["ordinal"] = i
    with pytest.raises(ValueError, match="original requirement denominator"):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "variant",
    (
        "self_join",
        "union_dag",
        "two_facades",
        "order_ordinary",
        "order_rebound",
        "order_completed",
        "producer_filter",
    ),
)
def test_later_operator_graph_is_structural_only(built, target, variant):
    _, checked, outcome = built(target, "O_named_later", variant)
    assert checked.verified, checked.issues
    layout = build_emission_layout(checked)
    assert verify_emission_layout(layout, checked)
    assert len(layout.definitions) == len(checked.plan.bindings.definitions)
    assert len(layout.uses) == len(checked.plan.input_uses)
    if variant in {"producer_filter", "self_join"}:
        # Slice6 implements this input's producer filter and Slice7 implements
        # the JOIN family that was self_join's only remaining restriction. The
        # retained source purpose and the historical BLOCKED outcome are
        # unchanged history; the named-chain structure each case owns is still
        # checked above, and self_join's shared-producer structure below.
        assert outcome.status == "VERIFIED", outcome.status
        assert outcome.artifact is not None
        public = probe.decode_public(serialize_project_sql_emission(outcome))
        assert "blockers" not in public
        assert public["sql"] == outcome.artifact.rendered.sql.decode()
    else:
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        public = probe.decode_public(serialize_project_sql_emission(outcome))
        assert "sql" not in public and public["artifact"] is None
        assert "PIE-B1003" in [b["code"] for b in public["blockers"]]
    if variant in {"self_join", "two_facades", "union_dag"}:
        repeated = [
            (a, b)
            for i, a in enumerate(layout.uses)
            for b in layout.uses[i + 1 :]
            if a.producer is b.producer and a.consumer is b.consumer
        ]
        assert repeated
        for a, b in repeated:
            assert (
                a.original is not b.original and a.original.edge is not b.original.edge
            )
            assert a.bindings[0].terminal is b.bindings[0].terminal
            assert a.bindings[0].input_port is not b.bindings[0].input_port
        if variant == "two_facades":
            a, b = repeated[0]
            assert a.original.origin_path is not b.original.origin_path
            assert a.original.binding is not b.original.binding
    if variant == "order_rebound":
        assert (
            type(layout.definitions[-1].original.entry).__name__
            == "ProjectIRReboundExistingOutput"
        )
        ordered, limited = checked.plan.result_boundaries
        left, right = ordered.properties.ordering, limited.properties.ordering
        assert (
            type(left).__name__
            == type(right).__name__
            == "ProjectIRProvidedRelationOrdering"
        )
        assert (
            left is not right
            and left.items is right.items
            and left.output is not right.output
        )
    elif variant in {"order_ordinary", "order_completed"}:
        assert checked.plan.orders
        assert all(
            type(order.source).__name__ == "ProjectRelationOrdering"
            for order in checked.plan.orders
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_definition",
        "missing_terminal",
        "collapsed_use",
        "wrong_terminal",
        "foreign_port",
        "cycle",
    ),
)
def test_layout_corruptions_fail_against_original_inventory(built, mutation):
    _, checked, outcome = built()
    _, _, foreign_outcome = built("mysql")
    artifact, foreign = outcome.artifact, foreign_outcome.artifact
    assert artifact is not None and foreign is not None
    layout = artifact.request.layout
    if mutation == "missing_definition":
        changed = replace(layout, definitions=layout.definitions[1:])
    elif mutation == "missing_terminal":
        changed = replace(
            layout,
            definitions=(
                layout.definitions[0],
                replace(
                    layout.definitions[1],
                    terminals=layout.definitions[1].terminals[:-1],
                ),
                *layout.definitions[2:],
            ),
        )
    elif mutation == "collapsed_use":
        changed = replace(layout, uses=layout.uses[:-1])
    else:
        use = layout.uses[-1]
        link = use.bindings[0]
        if mutation == "wrong_terminal":
            changed_use = replace(
                use,
                bindings=(
                    replace(link, terminal=layout.definitions[0].terminals[0]),
                    *use.bindings[1:],
                ),
            )
        elif mutation == "foreign_port":
            changed_use = replace(
                use,
                bindings=(
                    replace(
                        link,
                        input_port=foreign.request.layout.uses[-1]
                        .bindings[0]
                        .input_port,
                    ),
                    *use.bindings[1:],
                ),
            )
        else:
            changed_use = replace(use, producer=use.consumer)
        changed = replace(layout, uses=(*layout.uses[:-1], changed_use))
    assert not verify_emission_layout(changed, checked)


@pytest.mark.parametrize(
    "mutation",
    (
        "immediate_port",
        "representation",
        "reversed_ctes",
        "missing_cte",
        "capture",
        "bytes",
        "unicode_range",
        "requirements",
        "premise",
        "root",
        "contract",
    ),
)
def test_complete_artifact_rejects_coherent_and_local_grafts(built, mutation):
    _, _, outcome = built()
    artifact = outcome.artifact
    assert artifact is not None
    ast = artifact.ast
    changed = artifact
    if mutation in {"immediate_port", "representation"}:
        column = ast.columns[0]
        column = (
            replace(column, producer=ast.ctes[0].body.columns[0].producer)
            if mutation == "immediate_port"
            else replace(column, source_field=ast.columns[1].source_field)
        )
        changed = replace(
            artifact, ast=replace(ast, columns=(column, *ast.columns[1:]))
        )
    elif mutation == "reversed_ctes":
        changed = replace(artifact, ast=replace(ast, ctes=tuple(reversed(ast.ctes))))
    elif mutation == "missing_cte":
        changed = replace(
            artifact,
            ast=replace(ast, ctes=ast.ctes[1:]),
            generated_requirements=artifact.generated_requirements[8:],
        )
    elif mutation == "capture":
        changed = replace(
            artifact,
            ast=replace(
                ast, scan=replace(ast.scan, symbol=replace(ast.scan.symbol, name="p0"))
            ),
        )
    elif mutation == "bytes":
        changed = replace(
            artifact,
            rendered=replace(
                artifact.rendered,
                sql=artifact.rendered.sql.replace(b'FROM "p0"', b'FROM "p1"'),
            ),
        )
    elif mutation == "unicode_range":
        events = list(artifact.rendered.events)
        index = next(
            i
            for i, e in enumerate(events)
            if b"\xc3\xa9" in artifact.rendered.sql[e.start : e.end]
        )
        events[index] = replace(events[index], end=events[index].end - 1)
        changed = replace(
            artifact, rendered=replace(artifact.rendered, events=tuple(events))
        )
    elif mutation == "requirements":
        changed = replace(artifact, original_requirements=(), generated_requirements=())
    elif mutation == "premise":
        changed = replace(
            artifact,
            generated_requirements=(
                replace(artifact.generated_requirements[0], premises=()),
                *artifact.generated_requirements[1:],
            ),
        )
    elif mutation == "root":
        _, _, other = built("mysql")
        assert other.artifact is not None
        changed = replace(artifact, request=other.artifact.request)
    else:
        changed = replace(
            artifact,
            request=graft(
                artifact.request,
                normalized_bytes=artifact.request.normalized_bytes.replace(
                    b'"pietto.emission-contract.v1"', b'"wrong"'
                ),
            ),
        )
    assert not verify_project_sql_emission(changed, artifact.request).verified
    rejected = probe.decode_public(
        serialize_project_sql_emission(replace(outcome, artifact=changed))
    )
    assert rejected["status"] == "BLOCKED" and rejected["artifact"] is None
    assert rejected["blockers"][0]["code"] == "PIE-B1008"


@pytest.mark.parametrize(
    "mutation",
    (
        "forward_reference",
        "alias_capture",
        "immediate_terminal",
        "physical_provenance",
        "coordinated_requirements",
        "range",
        "premise",
    ),
)
def test_independent_named_public_consumer_rejects_mutations(built, mutation):
    _, _, outcome = built()
    document = json.loads(serialize_project_sql_emission(outcome))
    if mutation == "forward_reference":
        document["sql"] = document["sql"].replace('FROM "p0"', 'FROM "p1"')
    elif mutation == "alias_capture":
        document["sql"] = document["sql"].replace('"s1"', '"s0"')
    elif mutation == "immediate_terminal":
        interval = next(
            r
            for r in document["ranges"]
            if r["role"] == "column" and r["subject"]["kind"] == "result_port"
        )
        interval["subject"] = {"kind": "source_port", "position": 0}
    elif mutation == "physical_provenance":
        document["columns"][0]["correspondence"]["source_port"]["position"] = 0
    elif mutation == "coordinated_requirements":
        document["requirements"] = []
    elif mutation == "premise":
        next(r for r in document["requirements"] if r["kind"] == "cte_definition")[
            "premises"
        ] = []
    else:
        document["ranges"][0]["end"] = True
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize(
    "mutation",
    (
        "erase",
        "foreign_module",
        "wrong_role",
        "scope_swap",
        "import_hops",
        "origin_owner",
        "duplicate_module",
    ),
)
def test_named_public_provenance_is_coherent_without_authenticating_sources(
    built, mutation
):
    _, _, outcome = built("postgres", "N_imported_chain", "bag")
    document = json.loads(serialize_project_sql_emission(outcome))
    original_sql = document["sql"]
    if mutation == "erase":
        for interval in document["ranges"]:
            interval["origins"] = []
    elif mutation == "foreign_module":
        for interval in document["ranges"]:
            for origin in interval["origins"]:
                for source in origin["sources"]:
                    source["path"] = source["location"]["path"] = "foreign.pietto"
    elif mutation == "duplicate_module":
        document["request"]["sources"].append(
            deepcopy(document["request"]["sources"][0])
        )
    else:
        selected = next(
            r for r in document["ranges"] if r["subject"]["kind"] == "selected_plan"
        )["origins"][0]
        for interval in document["ranges"]:
            if mutation == "wrong_role" and interval["subject"] == {
                "kind": "definition",
                "position": 1,
            }:
                interval["origins"][0]["role"] = "selected_owner"
            elif mutation == "scope_swap" and interval["subject"] == {
                "kind": "result_port",
                "position": 0,
            }:
                interval["origins"][0]["sources"] = deepcopy(selected["sources"])
            elif mutation == "import_hops" and interval["subject"] == {
                "kind": "input_use",
                "position": 1,
            }:
                for origin in interval["origins"]:
                    origin["sources"] = [
                        s
                        for s in origin["sources"]
                        if s["kind"] not in {"import_item", "export_item"}
                    ]
            elif mutation == "origin_owner" and interval["subject"] == {
                "kind": "definition",
                "position": 1,
            }:
                interval["origins"][0]["position"] = selected["position"]
    assert document["sql"] == original_sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_imported_decimal_type_alias_keeps_additional_provenance(tmp_path, target):
    item = probe.fixture(target, "N_imported_chain", "bag")
    sources = dict(item["source"])
    sources["types.pietto"] = "type Money = Decimal(9, 2)\nexport:\n    type Money\n"
    sources["a.pietto"] = 'import "types.pietto":\n    type Money\n' + sources[
        "a.pietto"
    ].replace("money: Decimal(9, 2)", "money: Money")
    _, outcome = probe.build_case(tmp_path, sources, item["contract"])
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert public["columns"][3]["logical_type"]["parameters"] == {
        "precision": 9,
        "scale": 2,
    }
    assert any(
        s["path"] == "types.pietto"
        for interval in public["ranges"]
        for origin in interval["origins"]
        for s in origin["sources"]
    )


def test_named_inspection_never_calls_construction_or_rendering(built, monkeypatch):
    from pietto._project import project_sql_emission as emission
    from pietto._project import project_sql_emission_ast as ast
    from pietto._project import project_sql_emission_contract as contract
    from pietto._project import project_sql_emission_rendering as rendering
    from pietto._project import project_sql_emission_scopes as scopes

    _, checked, outcome = built()
    artifact = outcome.artifact
    assert artifact is not None
    data = serialize_project_sql_emission(outcome)

    def forbidden(*args, **kwargs):
        raise AssertionError("construction during independent inspection")

    for module, name in (
        (emission, "build_sql_ast"),
        (emission, "build_requirements"),
        (emission, "render_sql"),
        (ast, "build_sql_ast"),
        (ast, "build_requirements"),
        (rendering, "render_sql"),
        (scopes, "build_emission_layout"),
        (contract, "build_emission_layout"),
        (contract, "_decimal_precision_scale_fact"),
        (contract, "prepare_project_sql_emission"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    assert verify_emission_layout(artifact.request.layout, checked)
    assert verify_project_sql_emission(artifact, artifact.request).verified
    assert serialize_project_sql_emission(outcome) == data
    monkeypatch.setattr(emission, "serialize_project_sql_emission", forbidden)
    monkeypatch.setattr(emission, "verify_project_sql_emission", forbidden)
    assert probe.decode_public(data)["status"] == "VERIFIED"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_named_case_premises_and_final_label_limits(built, tmp_path, target):
    item, checked, _ = built(target)
    contract = json.loads(item["contract"])
    contract["environment"] = [
        p for p in contract["environment"] if p["key"] != "identifier_case"
    ]
    missing = emit_project_sql(checked, probe.encoded(contract))
    assert "PIE-B1004" in [b.code for b in missing.blockers]
    contract["environment"].append(
        {"key": "identifier_case", "scope": "statement", "value": "incompatible"}
    )
    conflict = emit_project_sql(checked, probe.encoded(contract))
    assert "PIE-B1005" in [b.code for b in conflict.blockers]
    limit = 63 if target == "postgres" else 256
    for count, expected in ((limit, "VERIFIED"), (limit + 1, "BLOCKED")):
        source = item["source"].replace("display_text = txt2", "x" * count + " = txt2")
        _, outcome = probe.build_case(tmp_path / str(count), source, item["contract"])
        assert outcome.status == expected
        if expected == "BLOCKED":
            assert "PIE-B1002" in [b.code for b in outcome.blockers]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_statement_premise_in_source_description_is_consumed(built, target):
    item, checked, _ = built(target)
    contract = json.loads(item["contract"])
    naming = contract["environment"].pop()
    assert naming["key"] == "identifier_case"
    contract["sources"][0]["premises"].append(naming)
    outcome = emit_project_sql(checked, probe.encoded(contract))
    assert outcome.status == "VERIFIED"
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert all(
        r["premises"] == [4]
        for r in public["requirements"]
        if r["denominator"] == "generated" and r["rule"] == "R03"
    )


@pytest.mark.parametrize(
    "case,variant", (("G_emission_table_bag", "bag"), ("M_named_chain", "table_bag"))
)
@pytest.mark.parametrize("placement", ("environment", "source"))
@pytest.mark.parametrize(
    "resource,ceiling",
    (
        ("sql_bytes", 8 * 1024 * 1024),
        ("artifact_bytes", 16 * 1024 * 1024),
        ("nodes", 32768),
        ("columns", 1664),
    ),
)
def test_public_consumer_enforces_each_scoped_resource_limit(
    built, case, variant, placement, resource, ceiling
):
    item, checked, _ = built("postgres", case, variant)
    contract = json.loads(item["contract"])
    declarations = (
        contract["environment"]
        if placement == "environment"
        else contract["sources"][0]["premises"]
    )
    declarations.append(
        {"key": "resource_limits", "scope": "statement", "value": {resource: ceiling}}
    )
    outcome = emit_project_sql(checked, probe.encoded(contract))
    assert outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    if placement == "environment":
        document["request"]["contract"]["environment"][-1]["value"][resource] = 1
        document["target"]["environment"][-1]["value"][resource] = 1
    else:
        document["request"]["contract"]["sources"][0]["premises"][-1]["value"][
            resource
        ] = 1
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_direct_public_identifier_rules_reject_nul_without_range_changes(built, target):
    _, _, outcome = built(target, "G_emission_table_bag", "bag")
    document = json.loads(serialize_project_sql_emission(outcome))
    old = document["columns"][0]["label"]
    new = "\0" + old[1:]
    quote = '"' if target == "postgres" else "`"
    original_length = len(document["sql"].encode())
    document["columns"][0]["label"] = new
    document["sql"] = document["sql"].replace(quote + old + quote, quote + new + quote)
    assert len(document["sql"].encode()) == original_length
    with pytest.raises(ValueError, match="unrepresentable identifier"):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("depth", (2, 8, 12))
def test_layout_retains_repeated_dag_once_per_definition(
    tmp_path, record_property, depth
):
    item = probe.fixture("postgres")
    header = item["source"].split("table result:", 1)[0]
    source = header + "table p0:\n    from rows\n    select:\n        id\n"
    source += "".join(
        f"table p{i}:\n    union all:\n        from p{i - 1}\n        from p{i - 1}\n"
        for i in range(1, depth + 1)
    )
    source += f"query result:\n    from p{depth}\n    select:\n        id\n"
    checked, outcome = probe.build_case(tmp_path, source, item["contract"])
    started = perf_counter()
    layout = build_emission_layout(checked)
    assert verify_emission_layout(layout, checked)
    record_property("layout_and_verification_seconds", perf_counter() - started)
    record_property("layout_definitions", len(layout.definitions))
    record_property("layout_uses", len(layout.uses))
    assert len(layout.definitions) == depth + 3
    assert len(layout.uses) == 2 * depth + 2
    assert sum(len(u.bindings) for u in layout.uses) == 2 * depth + 6
    assert outcome.status == "BLOCKED" and outcome.artifact is None


@pytest.mark.parametrize("depth", (1, 4, 8))
def test_flat_cte_sizes_are_measured_and_bounded(tmp_path, record_property, depth):
    item = probe.fixture("postgres", "M_named_chain", "table_bag")
    header = item["source"].split("table first:", 1)[0]
    source = header
    previous = "rows"
    for i in range(depth):
        source += f"table p{i}:\n    from {previous}\n    select:\n        id\n"
        previous = f"p{i}"
    source += f"query result:\n    from {previous}\n    select:\n        id\n"
    checked, outcome = probe.build_case(tmp_path, source, item["contract"])
    assert outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert isinstance(artifact.ast, SQLSelect)
    assert len(artifact.ast.ctes) == depth
    assert all(not cte.body.ctes for cte in artifact.ast.ctes)
    public = serialize_project_sql_emission(outcome)
    assert probe.decode_public(public)["status"] == "VERIFIED"
    actual_nodes = []
    for cte in artifact.ast.ctes:
        actual_nodes.extend((cte, cte.symbol, *cte.columns))
    for body in (*[cte.body for cte in artifact.ast.ctes], artifact.ast):
        actual_nodes.extend((body, body.scan, body.scan.symbol))
        for column in body.columns:
            actual_nodes.extend((column, column.symbol))
    nodes = len({id(node) for node in actual_nodes})
    assert nodes == len(actual_nodes) == 8 * depth + 5
    record_property("generated_nodes", nodes)
    record_property("cte_count", depth)
    record_property("select_nesting_depth", 1)
    record_property("sql_bytes", len(artifact.rendered.sql))
    record_property("artifact_bytes", len(public))
    for resource, actual in (
        ("nodes", nodes),
        ("sql_bytes", len(artifact.rendered.sql)),
    ):
        contract = json.loads(item["contract"])
        contract["environment"].append(
            {
                "key": "resource_limits",
                "scope": "statement",
                "value": {resource: actual},
            }
        )
        assert emit_project_sql(checked, probe.encoded(contract)).status == "VERIFIED"
        contract["environment"][-1]["value"][resource] -= 1
        blocked = emit_project_sql(checked, probe.encoded(contract))
        assert blocked.status == "BLOCKED" and any(
            b.code == "PIE-B1007" for b in blocked.blockers
        )
