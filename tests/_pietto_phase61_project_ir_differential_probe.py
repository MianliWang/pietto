from __future__ import annotations

import argparse
from copy import copy
from dataclasses import replace
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

import pietto._project.project_ir as project_ir
import pietto._project.project_ir_construction as construction
import pietto._project.project_ir_inspection as inspection
import pietto._project.project_ir_properties as properties
import pietto._project.project_ir_pure_boundary as pure
import pietto._project.project_ir_verification as verification
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_ir_pipeline import (
    ProjectIRPipelineResult,
    build_project_ir_pipeline,
)


OBSERVATION_FORMAT = "pietto.phase61-project-ir-differential.v1"
PROJECT_FILE_ITEMS = (
    (
        "a.pietto",
        'import "b.pietto":\n    table Public as Input\n'
        "query final:\n"
        "    from consumer\n"
        "    select:\n"
        "        id\n"
        "query consumer:\n"
        "    from Input\n"
        "    select:\n"
        "        id\n"
        "query second:\n"
        "    from Input\n"
        "    select:\n"
        "        id\n"
        "query aggregate_only:\n"
        "    from Input\n"
        "    select:\n"
        "        total = sum(amount)\n"
        "query full:\n"
        "    from Input\n"
        "    let:\n"
        "        floor = 0\n"
        "    where id > floor\n"
        "    group by:\n"
        "        category\n"
        "    select:\n"
        "        category\n"
        "        total = sum(amount)\n"
        "        ranking = row_number() window child\n"
        "    window child = base\n"
        "    window base:\n"
        "        partition by:\n"
        "            category\n"
        "        order by:\n"
        "            total desc\n"
        "    satisfying:\n"
        "        total > 0\n"
        "    order by:\n"
        "        ranking\n"
        "    limit 5\n"
        "query broken:\n"
        "    from Input\n"
        "    select:\n"
        "        missing\n",
    ),
    (
        "b.pietto",
        'import "c.pietto":\n    table projected as Public\n'
        "export:\n"
        "    table Public\n",
    ),
    (
        "c.pietto",
        "shape Row:\n"
        "    id: Int not null\n"
        "    amount: Int nullable\n"
        "    category: Text nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount\n"
        "        category\n"
        "export:\n"
        "    table projected\n",
    ),
    (
        "d.pietto",
        "shape Other:\n"
        "    key: Int not null\n"
        'source other: Other is postgres.table("other")\n'
        "query other_result:\n"
        "    from other\n"
        "    select:\n"
        "        key\n",
    ),
)
CYCLE_FILE_ITEMS = (
    (
        "main.pietto",
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query okay:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "query a:\n"
        "    from b\n"
        "    select:\n"
        "        id\n"
        "query b:\n"
        "    from a\n"
        "    select:\n"
        "        id\n",
    ),
)


def _write_project(
    root: Path,
    file_items: tuple[tuple[str, str], ...],
    *,
    reverse_creation: bool,
) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    items = file_items[::-1] if reverse_creation else file_items
    for path, source in items:
        (root / path).write_text(source, encoding="utf-8")
    return root


def _semantic_project(root: Path) -> ProjectSemanticResult:
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _allocation(
    *,
    node: int = 0,
    output: int = 0,
    slot: int = 0,
    use: int = 0,
) -> construction.ProjectIRAllocationState:
    return construction.ProjectIRAllocationState(
        scope=project_ir.ProjectIRSnapshotScope(),
        next_plan_node_position=node,
        next_output_value_position=output,
        next_input_slot_position=slot,
        next_use_position=use,
    )


def _build(
    root: Path,
    file_items: tuple[tuple[str, str], ...],
    *,
    reverse_creation: bool,
) -> tuple[ProjectSemanticResult, ProjectIRPipelineResult]:
    semantic = _semantic_project(
        _write_project(root, file_items, reverse_creation=reverse_creation)
    )
    return semantic, build_project_ir_pipeline(
        semantic_result=semantic,
        allocation=_allocation(),
    )


def _identity_value(identity) -> list[object]:
    nominal = identity.identity
    return [
        nominal.module_path,
        identity.module_position,
        identity.declaration_position,
        nominal.namespace.value,
        nominal.declaration_kind.value,
        nominal.declared_name,
    ]


def _field_identity_value(identity) -> list[object]:
    return [
        *_identity_value(identity.owner),
        identity.kind.value,
        identity.field_position,
        identity.name,
    ]


def _fragment_name(fragment) -> str:
    return fragment.semantic_facts.owner.identity.declared_name


def _origin_hop_count(edge) -> int:
    origin = edge.authority.dependency.origin_path
    assert origin is not None
    return len(origin.hops)


def _relation_value(fragment) -> list[object]:
    fields: list[list[object]] = []
    if type(fragment) is construction.ProjectIRConcreteSingleRelationFragment:
        row_shape = fragment.root_relation_output.row_shape
        assert type(row_shape) is properties.ProjectIRRowShape
        fields = [
            _field_identity_value(item.anchor.identity) for item in row_shape.fields
        ]
    return [
        _identity_value(fragment.subject.anchor.identity),
        fragment.subject.state.value,
        type(fragment.subject.evidence).__name__,
        fields,
    ]


def _provided_value(property_) -> list[object]:
    payload: object
    if type(property_) is properties.ProjectIRProvidedOutputShape:
        payload = type(property_.output.row_shape).__name__
    elif type(property_) is properties.ProjectIRProvidedBagMultiplicity:
        payload = "bag"
    elif type(property_) is properties.ProjectIRProvidedClosedBindings:
        payload = []
    elif type(property_) is properties.ProjectIRProvidedRelationOrdering:
        payload = len(property_.items)
    elif type(property_) is properties.ProjectIRProvidedLocalGrainEvidence:
        payload = len(property_.occurrences)
    elif type(property_) is properties.ProjectIRProvidedCardinalityUpperBound:
        payload = property_.upper_bound
    elif type(property_) is properties.ProjectIRProvidedEvaluationPolicy:
        payload = [property_.policy.identity.name, property_.policy.kind.value]
    else:
        assert type(property_) is properties.ProjectIRUnavailableProvidedProperty
        payload = property_.availability.value
    return [
        property_.output.occurrence.ref.position,
        property_.property_slot.value,
        type(property_).__name__,
        payload,
    ]


def _effect_value(effect: properties.ProjectIREffectEvidence) -> list[object]:
    return [
        effect.output.occurrence.ref.position,
        effect.determinism.value,
        effect.error_behavior.value,
        effect.side_effects.value,
        effect.evaluation_count.value,
    ]


def _query_observation(
    result: ProjectIRPipelineResult,
    *,
    reverse: bool,
) -> list[list[object]]:
    keys = (("a.pietto", "full"), ("a.pietto", "broken"))
    order = keys[::-1] if reverse else keys
    values: dict[tuple[str, str], list[object]] = {}
    for key in order:
        module_path, name = key
        fragment = next(
            item
            for item in result.project_plan.fragments
            if item.semantic_facts.owner.identity.module_path == module_path
            and _fragment_name(item) == name
        )
        relations = inspection.query_project_ir_relations(
            result.inspection,
            fragment.subject.anchor.identity,
        )
        why_not = inspection.query_project_ir_non_concrete(
            result.inspection,
            fragment.subject.anchor.identity,
        )
        values[key] = [
            module_path,
            name,
            len(relations),
            [item.subject.state.value for item in why_not],
        ]
    return [values[key] for key in keys]


def _project_observation(
    result: ProjectIRPipelineResult,
    *,
    query_reverse: bool,
) -> dict[str, object]:
    plan = result.project_plan
    stage = result.evaluation_context_stage
    structural = plan.structural_stage
    operators_by_node = {
        operator.node: operator
        for fragment in plan.fragments
        for operator in fragment.logical_stage.operators
    }
    return {
        "relations": [_relation_value(item) for item in plan.fragments],
        "operators": [
            [
                *_identity_value(fragment.subject.anchor.identity),
                [operator.kind.value for operator in fragment.logical_stage.operators],
            ]
            for fragment in plan.fragments
        ],
        "nodes": [
            [
                node.ref.position,
                *_identity_value(node.anchor.identity),
                operators_by_node[node].kind.value,
            ]
            for node in structural.nodes
        ],
        "outputs": [
            [
                output.ref.position,
                output.producer.ref.position,
                type(output.anchor).__name__,
            ]
            for output in structural.outputs
        ],
        "input_slots": [
            [slot.ref.position, slot.consumer.ref.position, slot.input_ordinal]
            for slot in structural.input_slots
        ],
        "uses": [
            [
                use.ref.position,
                use.output.ref.position,
                use.slot.ref.position,
                type(use).__name__,
                (
                    use.role.value
                    if type(use) is project_ir.ProjectIRUseOccurrence
                    else None
                ),
                (
                    use.source_order
                    if type(use) is project_ir.ProjectIRUseOccurrence
                    else None
                ),
            ]
            for use in structural.uses
        ],
        "cross_edges": [
            [
                _identity_value(edge.producer.subject.anchor.identity),
                _identity_value(edge.consumer.subject.anchor.identity),
                edge.use.ref.position,
                edge.input_slot.ref.position,
                edge.compatibility.status.value,
                edge.use.source_order,
                _origin_hop_count(edge),
            ]
            for edge in plan.cross_relation_edges
        ],
        "provided_properties": [
            _provided_value(property_)
            for fragment in plan.fragments
            for property_ in fragment.property_stage.provided
        ],
        "effects": [
            _effect_value(effect)
            for fragment in plan.fragments
            for effect in fragment.property_stage.effects
        ],
        "aggregate_contexts": [
            [
                _fragment_name(context.fragment),
                context.operator.node.ref.position,
                context.incoming_flow.ref.position,
                len(context.group_keys),
                sum(
                    1
                    for property_ in context.fragment.property_stage.provided
                    if type(property_) is properties.ProjectIRProvidedLocalGrainEvidence
                    and property_.output is context.result_row_output
                ),
                [
                    [item.function, item.output_name, item.grouped, item.argument_count]
                    for item in context.aggregate_results
                ],
                context.readiness.status.value,
                [
                    context.input_effect.determinism.value,
                    context.result_effect.determinism.value,
                ],
                [
                    len(context.input_closed_bindings.bindings),
                    len(context.result_closed_bindings.bindings),
                ],
            ]
            for context in stage.aggregate_contexts
        ],
        "window_operator_contexts": [
            [
                _fragment_name(context.fragment),
                context.operator.node.ref.position,
                context.incoming_flow.ref.position,
                context.semantic_base_checkpoint.kind.value,
                context.stream_matches_semantic_base,
                [
                    len(context.stream_closed_bindings.bindings),
                    len(context.result_closed_bindings.bindings),
                ],
                [
                    context.stream_effect.determinism.value,
                    context.result_effect.determinism.value,
                ],
            ]
            for context in stage.window_operator_contexts
        ],
        "window_result_contexts": [
            [
                _fragment_name(context.operator_context.fragment),
                context.window_fact.selected_output_ordinal,
                context.stage_scalar_output.occurrence.ref.position,
                [
                    item.role.value
                    for item in context.project_fact.dependency_occurrences
                ],
                context.policy.policy.identity.name,
                context.policy.policy.kind.value,
                [
                    context.effect.determinism.value,
                    context.effect.error_behavior.value,
                    context.effect.side_effects.value,
                    context.effect.evaluation_count.value,
                ],
            ]
            for context in stage.window_result_contexts
        ],
        "verification": [
            result.verification.status.value,
            [
                [
                    issue.kind.value,
                    None
                    if issue.coordinate is None
                    else type(issue.coordinate).__name__,
                    None if issue.coordinate is None else issue.coordinate.position,
                ]
                for issue in result.verification.issues
            ],
        ],
        "topological": [
            node.ref.position for node in result.analysis_bundle.topological_order
        ],
        "reachability": [
            [
                entry.source.ref.position,
                [node.ref.position for node in entry.reachable],
            ]
            for entry in result.analysis_bundle.reachability
        ],
        "equivalence": [
            [
                _identity_value(item.left.subject.anchor.identity),
                _identity_value(item.right.subject.anchor.identity),
                item.status.value,
                [
                    [dimension.dimension.value, dimension.status.value]
                    for dimension in item.dimensions
                ],
            ]
            for item in result.analysis_bundle.equivalence_assessments
        ],
        "rewrite_readiness": [
            [
                _identity_value(item.assessment.left.subject.anchor.identity),
                _identity_value(item.assessment.right.subject.anchor.identity),
                item.status.value,
                [blocker.value for blocker in item.blockers],
            ]
            for item in result.analysis_bundle.rewrite_readiness
        ],
        "queries": _query_observation(result, reverse=query_reverse),
        "canonical_bytes": result.canonical_bytes.decode("utf-8"),
    }


def _unsafe_stage_without_last_aggregate(result: ProjectIRPipelineResult):
    stage = copy(result.evaluation_context_stage)
    assert stage.aggregate_contexts
    object.__setattr__(stage, "aggregate_contexts", stage.aggregate_contexts[:-1])
    return stage


def _invalid_observation(result: ProjectIRPipelineResult) -> dict[str, object]:
    invalid = verification.verify_project_ir_stage(
        _unsafe_stage_without_last_aggregate(result)
    )
    return {
        "status": invalid.status.value,
        "issues": [
            [
                issue.kind.value,
                None if issue.coordinate is None else type(issue.coordinate).__name__,
                None if issue.coordinate is None else issue.coordinate.position,
            ]
            for issue in invalid.issues
        ],
    }


def _field_value(record: pure.ProjectIRPureRecord, key: str) -> pure.ProjectIRPureValue:
    values = tuple(field.value for field in record.fields if field.key == key)
    assert len(values) == 1
    return values[0]


def _record_position(document: pure.ProjectIRPureDocument, kind: str) -> int:
    positions = tuple(
        position
        for position, record in enumerate(document.records)
        if record.kind == kind
    )
    assert positions
    return positions[0]


def _replace_record(
    document: pure.ProjectIRPureDocument,
    position: int,
    record: pure.ProjectIRPureRecord,
) -> pure.ProjectIRPureDocument:
    records = list(document.records)
    records[position] = record
    return replace(document, records=tuple(records))


def _replace_field(
    document: pure.ProjectIRPureDocument,
    record_position: int,
    key: str,
    value: pure.ProjectIRPureValue,
) -> pure.ProjectIRPureDocument:
    record = document.records[record_position]
    return _replace_record(
        document,
        record_position,
        replace(
            record,
            fields=tuple(
                replace(field, value=value) if field.key == key else field
                for field in record.fields
            ),
        ),
    )


def _pure_outcome(document: pure.ProjectIRPureDocument) -> list[object]:
    outcome = pure.evaluate_project_ir_document(document)
    return [outcome.status.value, outcome.record_position, outcome.field_position]


def _pure_rejections(result: ProjectIRPipelineResult) -> list[list[object]]:
    document = result.inspection_product.document
    header = 0
    fragment = _record_position(document, "fragment")
    node = _record_position(document, "node")
    output = _record_position(document, "output")
    use = _record_position(document, "use")

    bad_marker = _replace_field(
        document,
        header,
        "format",
        pure.project_ir_pure_enumeration("unknown.private.format"),
    )
    last_node = tuple(
        position
        for position, record in enumerate(document.records)
        if record.kind == "node"
    )[-1]
    last_node_ref = _field_value(document.records[last_node], "node").ref
    assert last_node_ref is not None
    non_dense = _replace_field(
        document,
        last_node,
        "node",
        pure.project_ir_pure_ref(
            pure.ProjectIRPortableRef(
                domain=last_node_ref.domain,
                position=last_node_ref.position + 1,
            )
        ),
    )
    first_node_ref = _field_value(document.records[node], "node").ref
    assert first_node_ref is not None
    wrong_domain = _replace_field(
        document,
        output,
        "producer",
        pure.project_ir_pure_ref(
            pure.ProjectIRPortableRef(
                domain=pure.ProjectIRPortableRefDomain.OUTPUT_VALUE,
                position=first_node_ref.position,
            )
        ),
    )
    dangling = _replace_field(
        document,
        output,
        "producer",
        pure.project_ir_pure_ref(
            pure.ProjectIRPortableRef(
                domain=pure.ProjectIRPortableRefDomain.PLAN_NODE,
                position=pure.PROJECT_IR_PURE_MAX_INTEGER,
            )
        ),
    )
    reordered = list(document.records)
    reordered[fragment], reordered[node] = reordered[node], reordered[fragment]
    section_order = replace(document, records=tuple(reordered))
    second_use = next(
        position
        for position in range(use + 1, len(document.records))
        if document.records[position].kind == "use"
    )
    other_slot = _field_value(document.records[second_use], "slot").ref
    assert other_slot is not None
    invalid_endpoint = _replace_field(
        document,
        use,
        "slot",
        pure.project_ir_pure_ref(other_slot),
    )
    return [
        ["wrong_format", *_pure_outcome(bad_marker)],
        ["non_dense_ref", *_pure_outcome(non_dense)],
        ["wrong_domain_ref", *_pure_outcome(wrong_domain)],
        ["dangling_ref", *_pure_outcome(dangling)],
        ["section_order", *_pure_outcome(section_order)],
        ["invalid_use_endpoint", *_pure_outcome(invalid_endpoint)],
    ]


def _cycle_observation(root: Path) -> dict[str, object]:
    _semantic, result = _build(
        root,
        CYCLE_FILE_ITEMS,
        reverse_creation=True,
    )
    non_concrete = result.project_plan.non_concrete_fragments
    return {
        "relations": [_relation_value(item) for item in result.project_plan.fragments],
        "non_concrete": [
            [
                _fragment_name(fragment),
                fragment.subject.state.value,
                type(fragment.subject.evidence).__name__,
                len(fragment.structural_stage.nodes),
                len(fragment.structural_stage.uses),
                len(
                    inspection.query_project_ir_non_concrete(
                        result.inspection,
                        fragment.subject.anchor.identity,
                    )
                ),
            ]
            for fragment in non_concrete
        ],
        "concrete": [
            _fragment_name(item) for item in result.project_plan.concrete_fragments
        ],
        "verification": [
            result.verification.status.value,
            [item.kind.value for item in result.verification.issues],
        ],
        "canonical_bytes": result.canonical_bytes.decode("utf-8"),
    }


def _construction(
    root: Path,
    *,
    reverse_operation_order: bool,
) -> tuple[ProjectSemanticResult, ProjectIRPipelineResult, dict[str, object]]:
    specifications = (
        (
            ("reverse-created", True),
            ("normal-created", False),
        )
        if reverse_operation_order
        else (
            ("normal-created", False),
            ("reverse-created", True),
        )
    )
    built: dict[str, tuple[ProjectSemanticResult, ProjectIRPipelineResult]] = {}
    for name, reverse_creation in specifications:
        built[name] = _build(
            root / name,
            PROJECT_FILE_ITEMS,
            reverse_creation=reverse_creation,
        )
    normal_semantic, normal = built["normal-created"]
    _reverse_semantic, reverse = built["reverse-created"]
    normal_value = _project_observation(
        normal,
        query_reverse=reverse_operation_order,
    )
    reverse_value = _project_observation(
        reverse,
        query_reverse=not reverse_operation_order,
    )
    assert normal_value == reverse_value
    assert normal.starting_allocation.scope is not reverse.starting_allocation.scope
    assert normal.project_plan.structural_stage.nodes[0].ref != (
        reverse.project_plan.structural_stage.nodes[0].ref
    )
    assert normal.canonical_bytes == reverse.canonical_bytes
    return normal_semantic, normal, normal_value


def observation(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    first_semantic, first, first_value = _construction(
        workspace / "forward",
        reverse_operation_order=False,
    )
    _second_semantic, second, second_value = _construction(
        workspace / "reverse",
        reverse_operation_order=True,
    )
    assert first_value == second_value
    assert first.starting_allocation.scope is not second.starting_allocation.scope
    assert first.project_plan.structural_stage.nodes[0].ref != (
        second.project_plan.structural_stage.nodes[0].ref
    )
    shifted = build_project_ir_pipeline(
        semantic_result=first_semantic,
        allocation=_allocation(node=7, output=11, slot=5, use=5),
    )
    assert shifted.starting_allocation.scope is not first.starting_allocation.scope
    assert shifted.project_plan.structural_stage.nodes[0].ref != (
        first.project_plan.structural_stage.nodes[0].ref
    )
    assert shifted.canonical_bytes != first.canonical_bytes
    return {
        "observation_format": OBSERVATION_FORMAT,
        "package_version": version("pietto"),
        "runtime_identities_distinct": True,
        "project": first_value,
        "shifted": {
            "starting_coordinates": [7, 11, 5, 5],
            "first_node": shifted.project_plan.structural_stage.nodes[0].ref.position,
            "canonical_bytes": shifted.canonical_bytes.decode("utf-8"),
        },
        "cycle": _cycle_observation(workspace / "cycle"),
        "invalid_verification": _invalid_observation(first),
        "pure_rejections": _pure_rejections(first),
    }


def render(value: object, workspace: Path) -> bytes:
    """Encode one observation exactly as the standalone probe emits it."""

    document = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=False,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert str(workspace).encode() not in document
    assert os.getcwd().encode() not in document
    irrelevant = os.environ.get("PIETTO_SLICE11_IRRELEVANT")
    if irrelevant is not None:
        assert irrelevant.encode() not in document
    assert b"0x" not in document
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    namespace = parser.parse_args(argv)
    sys.stdout.buffer.write(
        render(observation(namespace.workspace), namespace.workspace)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
