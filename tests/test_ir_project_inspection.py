from __future__ import annotations

from copy import copy
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import os
from pathlib import Path
import subprocess
import sys

import pytest

import pietto
import pietto._project as project_package
import pietto._project.project_ir as project_ir
import pietto._project.project_ir_composition as composition
import pietto._project.project_ir_construction as construction
import pietto._project.project_ir_evaluation_context as evaluation
import pietto._project.project_ir_inspection as inspection
import pietto._project.project_ir_operators as operators
import pietto._project.project_ir_pure_boundary as pure
import pietto._project.project_ir_verification as verification
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice9-private-inspection-query-canonical-serialization-pure-boundary-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owners",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "VERIFIED Analysis Admission",
    "Complete Private Inspection Projection",
    "Typed Winner-free Query Surface",
    "Portable Identity And Record Order",
    "Pure Total Boundary And Rejections",
    "Single Canonical Serializer",
    "Canonical Bytes Are Not Identity",
    "Determinism Immutability And Zero Mutation",
    "Focused Assurance",
    "Integration Boundaries And Non-goals",
    "Slice 10 Handoff",
    "Gate Lifecycle And Publication",
)


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
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
            "query grouped:\n"
            "    from Input\n"
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        category\n"
            "        total = sum(amount)\n"
            "query windowed:\n"
            "    from Input\n"
            "    select:\n"
            "        id\n"
            "        ranking = row_number() window:\n"
            "            order by:\n"
            "                id\n"
            "query full:\n"
            "    from Input\n"
            "    let:\n"
            "        adjusted = amount + id\n"
            "    where id > 0\n"
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        category\n"
            "        total = sum(adjusted)\n"
            "        ranking = row_number() window:\n"
            "            partition by:\n"
            "                category\n"
            "            order by:\n"
            "                total desc\n"
            "    satisfying:\n"
            "        sum(adjusted) > 0\n"
            "query broken:\n"
            "    from Input\n"
            "    select:\n"
            "        missing\n"
        ),
        "b.pietto": (
            'import "c.pietto":\n    table projected as Public\n'
            "export:\n"
            "    table Public\n"
        ),
        "c.pietto": (
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
            "    table projected\n"
        ),
        "d.pietto": (
            "shape Other:\n"
            "    key: Int not null\n"
            'source other: Other is postgres.table("other")\n'
            "query other_result:\n"
            "    from other\n"
            "    select:\n"
            "        key\n"
        ),
    }


def _semantic_project(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for path, source in _project_files().items():
        (root / path).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _build_bundle(
    semantic: ProjectSemanticResult,
    allocation: construction.ProjectIRAllocationState | None = None,
) -> verification.ProjectIRAnalysisBundle:
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    plan = composition.build_project_ir_project_plan(
        semantic_facts=facts,
        attribution=attribution,
        allocation=(
            construction.ProjectIRAllocationState(
                scope=project_ir.ProjectIRSnapshotScope()
            )
            if allocation is None
            else allocation
        ),
    )
    stage = evaluation.build_project_ir_evaluation_context_stage(plan)
    return verification.build_project_ir_analysis_bundle(
        verification.verify_project_ir_stage(stage)
    )


def _fragment(
    inspected: inspection.ProjectIRInspection,
    module_path: str,
    name: str,
) -> construction.ProjectIRSingleRelationFragment:
    matches = tuple(
        fragment
        for fragment in inspected.fragments
        if fragment.semantic_facts.owner.identity.module_path == module_path
        and fragment.semantic_facts.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _concrete(
    inspected: inspection.ProjectIRInspection,
    module_path: str,
    name: str,
) -> construction.ProjectIRConcreteSingleRelationFragment:
    fragment = _fragment(inspected, module_path, name)
    assert type(fragment) is construction.ProjectIRConcreteSingleRelationFragment
    return fragment


def test_controlling_contract_locks_inspection_pure_boundary_and_handoff() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == SPEC_HEADINGS
    )
    normalized = " ".join(document.split())
    for evidence in (
        "577511b9dd6dbf14dbd5dc3710bee0a3d86b92be",
        "c4bc106f54d31939c4681d4d1dd6bb10d519f78c",
        "33349469530",
        "A4/M4/D0",
        "pietto.project-ir-inspection.v1",
        "Project IR authority != inspection != query result != canonical bytes != persistent identity",
        "canonical-byte equality != Project occurrence identity",
        "ProjectIRInspectionProduct",
        "evaluate_project_ir_document",
        "Add Phase 61 Project IR inspection",
        "PASS — PHASE61_SLICE9_PRIVATE_INSPECTION_QUERY_CANONICAL_SERIALIZATION_"
        "PURE_BOUNDARY_END_TO_END",
        "Phase 61 Slice 10 — Real Authored Multi-Module Project IR E2E",
    ):
        assert evidence in normalized


def test_verified_bundle_builds_complete_private_immutable_inspection(
    tmp_path: Path,
) -> None:
    bundle = _build_bundle(_semantic_project(tmp_path))
    stage = bundle.stage
    plan = stage.project_plan
    start = plan.starting_allocation
    end = plan.ending_allocation
    product = inspection.build_project_ir_inspection(bundle)
    inspected = product.inspection
    assert inspected.analysis_bundle is bundle
    assert inspected.verification is bundle.verification
    assert inspected.fragments is plan.fragments
    assert inspected.nodes is plan.structural_stage.nodes
    assert inspected.input_slots is plan.structural_stage.input_slots
    assert inspected.uses is plan.structural_stage.uses
    assert inspected.cross_relation_edges is plan.cross_relation_edges
    assert inspected.reverse_uses is bundle.reverse_uses
    assert inspected.topological_order is bundle.topological_order
    assert inspected.reachability is bundle.reachability
    assert inspected.equivalence_assessments is bundle.equivalence_assessments
    assert inspected.rewrite_readiness is bundle.rewrite_readiness
    assert any(
        type(fragment) is construction.ProjectIRNonConcreteSingleRelationFragment
        for fragment in inspected.fragments
    )
    assert inspected.aggregate_contexts
    assert inspected.window_operator_contexts
    assert inspected.window_result_contexts
    assert product.document.records[0].kind == "header"
    assert product.document.records[-1].kind == "end"
    assert product.canonical_bytes.startswith(
        b"header\tformat=e:pietto.project-ir-inspection.v1"
    )
    assert stage.project_plan is plan
    assert plan.structural_stage is inspected.stage.project_plan.structural_stage
    assert plan.starting_allocation is start
    assert plan.ending_allocation is end
    assert inspection.__all__ == ()
    assert pure.__all__ == ()
    for carrier in (
        inspection.ProjectIRInspectionSummary,
        inspection.ProjectIRInspection,
        inspection.ProjectIRInspectionProduct,
        pure.ProjectIRPortableRef,
        pure.ProjectIRPureValue,
        pure.ProjectIRPureField,
        pure.ProjectIRPureRecord,
        pure.ProjectIRPureDocument,
        pure.ProjectIRPureOutcome,
    ):
        assert getattr(carrier, "__dataclass_params__").frozen
        assert hasattr(carrier, "__slots__")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    with pytest.raises(FrozenInstanceError):
        inspected.fragments = ()  # type: ignore[misc]


def test_typed_queries_return_complete_exact_buckets_without_winners(
    tmp_path: Path,
) -> None:
    inspected = inspection.build_project_ir_inspection(
        _build_bundle(_semantic_project(tmp_path))
    ).inspection
    projected = _concrete(inspected, "c.pietto", "projected")
    consumer = _concrete(inspected, "a.pietto", "consumer")
    second = _concrete(inspected, "a.pietto", "second")
    broken = _fragment(inspected, "a.pietto", "broken")
    assert inspection.query_project_ir_relations(
        inspected,
        consumer.subject.anchor.identity,
    ) == (consumer,)
    node = consumer.logical_stage.operators[0].node
    assert inspection.query_project_ir_nodes(inspected, node.ref) == (node,)
    output = projected.root_relation_output
    assert inspection.query_project_ir_outputs(inspected, output.occurrence.ref) == (
        output,
    )
    edge = next(
        edge for edge in inspected.cross_relation_edges if edge.consumer is consumer
    )
    assert inspection.query_project_ir_input_slots(inspected, edge.input_slot.ref) == (
        edge.input_slot,
    )
    assert inspection.query_project_ir_uses(inspected, edge.use.ref) == (edge.use,)
    assert inspection.query_project_ir_cross_edges(inspected, edge.use.ref) == (edge,)
    outgoing = inspection.query_project_ir_outgoing_uses(inspected, projected.root.ref)
    expected_outgoing = tuple(
        use for use in inspected.uses if use.output.producer is projected.root
    )
    assert outgoing == expected_outgoing
    assert len(outgoing) >= 2
    assert inspection.query_project_ir_incoming_uses(inspected, node.ref) == tuple(
        use for use in inspected.uses if use.slot.consumer is node
    )
    properties = inspection.query_project_ir_properties(
        inspected,
        output.occurrence.ref,
    )
    assert properties
    assert all(property_.output is output for property_ in properties)
    effects = inspection.query_project_ir_effects(inspected, output.occurrence.ref)
    assert len(effects) == 1 and effects[0].output is output
    aggregate = _concrete(inspected, "a.pietto", "grouped")
    group_node = next(
        operator.node
        for operator in aggregate.logical_stage.operators
        if operator.kind is operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    )
    assert inspection.query_project_ir_evaluation_contexts(inspected, group_node.ref)
    assert inspection.query_project_ir_non_concrete(
        inspected,
        broken.subject.anchor.identity,
    ) == (broken,)
    assert inspection.query_project_ir_reachability(inspected, projected.root.ref)
    assessments = inspection.query_project_ir_equivalence(
        inspected,
        consumer.subject.anchor.identity,
        second.subject.anchor.identity,
    )
    assert len(assessments) == 1
    assert assessments[0].left is not assessments[0].right
    readiness = inspection.query_project_ir_rewrite_readiness(
        inspected,
        consumer.subject.anchor.identity,
        second.subject.anchor.identity,
    )
    assert len(readiness) == 1
    assert readiness[0].status is verification.ProjectIRRewriteReadinessStatus.BLOCKED
    foreign = project_ir.ProjectIRPlanNodeRef(
        scope=project_ir.ProjectIRSnapshotScope(),
        position=node.ref.position,
    )
    with pytest.raises(ValueError, match="snapshot"):
        inspection.query_project_ir_nodes(inspected, foreign)


def _field_value(
    record: pure.ProjectIRPureRecord,
    key: str,
) -> pure.ProjectIRPureValue:
    matches = tuple(field.value for field in record.fields if field.key == key)
    assert len(matches) == 1
    return matches[0]


def _field_ref(
    record: pure.ProjectIRPureRecord,
    key: str,
) -> pure.ProjectIRPortableRef:
    ref = _field_value(record, key).ref
    assert ref is not None
    return ref


def _record_position(document: pure.ProjectIRPureDocument, kind: str) -> int:
    matches = tuple(
        position
        for position, record in enumerate(document.records)
        if record.kind == kind
    )
    assert matches
    return matches[0]


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
    fields_ = tuple(
        replace(field, value=value) if field.key == key else field
        for field in record.fields
    )
    return _replace_record(document, record_position, replace(record, fields=fields_))


def test_verified_admission_is_exclusive_and_invalid_bundle_is_rejected(
    tmp_path: Path,
) -> None:
    bundle = _build_bundle(_semantic_project(tmp_path))
    issue = verification.ProjectIRVerificationIssue(
        kind=verification.ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION
    )
    invalid_result = copy(bundle.verification)
    object.__setattr__(
        invalid_result,
        "status",
        verification.ProjectIRVerificationStatus.INVALID,
    )
    object.__setattr__(invalid_result, "issues", (issue,))
    invalid_bundle = copy(bundle)
    object.__setattr__(invalid_bundle, "verification", invalid_result)
    with pytest.raises(ValueError, match="VERIFIED"):
        inspection.build_project_ir_inspection(invalid_bundle)
    with pytest.raises(TypeError):
        inspection.build_project_ir_inspection(bundle.stage)  # type: ignore[arg-type]


def test_canonical_order_bytes_and_runtime_scope_identity_remain_separate(
    tmp_path: Path,
) -> None:
    first_bundle = _build_bundle(_semantic_project(tmp_path / "first"))
    second_bundle = _build_bundle(_semantic_project(tmp_path / "second"))
    first = inspection.build_project_ir_inspection(first_bundle)
    second = inspection.build_project_ir_inspection(second_bundle)
    assert first.inspection.summary.scope is not second.inspection.summary.scope
    assert first.inspection.nodes[0].ref != second.inspection.nodes[0].ref
    assert first.canonical_bytes == second.canonical_bytes
    assert first.canonical_bytes is not second.canonical_bytes
    assert b"ProjectIRSnapshotScope" not in first.canonical_bytes
    assert b"0x" not in first.canonical_bytes
    assert inspection.serialize_project_ir_inspection(first.inspection) == (
        first.canonical_bytes
    )

    node_records = tuple(
        record for record in first.document.records if record.kind == "node"
    )
    direct_positions = tuple(
        _field_ref(record, "node").position for record in node_records
    )
    assert direct_positions == tuple(
        node.ref.position for node in first.inspection.nodes
    )
    topological_records = tuple(
        record for record in first.document.records if record.kind == "topological"
    )
    topological_positions = tuple(
        _field_ref(record, "node").position for record in topological_records
    )
    assert topological_positions == tuple(
        node.ref.position for node in first.inspection.topological_order
    )
    assert direct_positions != topological_positions

    shifted = _build_bundle(
        _semantic_project(tmp_path / "shifted"),
        construction.ProjectIRAllocationState(
            scope=project_ir.ProjectIRSnapshotScope(),
            next_plan_node_position=7,
            next_output_value_position=11,
            next_input_slot_position=5,
            next_use_position=5,
        ),
    )
    shifted_product = inspection.build_project_ir_inspection(shifted)
    assert shifted_product.canonical_bytes != first.canonical_bytes
    assert (
        first.inspection.nodes[0]
        is first_bundle.stage.project_plan.structural_stage.nodes[0]
    )
    source = (REPO_ROOT / "src/pietto/_project/project_ir_inspection.py").read_text(
        encoding="utf-8"
    )
    pure_source = (
        REPO_ROOT / "src/pietto/_project/project_ir_pure_boundary.py"
    ).read_text(encoding="utf-8")
    assert "_encode_document" not in source
    assert pure_source.count("def _encode_document") == 1


def test_pure_evaluator_accepts_reference_document_and_normalizes_malformed_inputs(
    tmp_path: Path,
) -> None:
    product = inspection.build_project_ir_inspection(
        _build_bundle(_semantic_project(tmp_path))
    )
    document = product.document
    accepted = pure.evaluate_project_ir_document(document)
    assert accepted.status is pure.ProjectIRPureStatus.OK
    assert accepted.canonical_bytes == product.canonical_bytes

    header = 0
    fragment = _record_position(document, "fragment")
    node = _record_position(document, "node")
    output = _record_position(document, "output")
    use = _record_position(document, "use")
    topological = _record_position(document, "topological")

    bad_marker = _replace_field(
        document,
        header,
        "format",
        pure.project_ir_pure_enumeration("unknown.private.format"),
    )
    unknown_kind = _replace_record(
        document,
        fragment,
        replace(document.records[fragment], kind="unknown_record"),
    )
    wrong_arity = _replace_record(
        document,
        fragment,
        replace(
            document.records[fragment],
            fields=document.records[fragment].fields[:-1],
        ),
    )
    wrong_key_fields = list(document.records[fragment].fields)
    wrong_key_fields[0] = replace(wrong_key_fields[0], key="wrong")
    wrong_key = _replace_record(
        document,
        fragment,
        replace(document.records[fragment], fields=tuple(wrong_key_fields)),
    )
    wrong_tag = _replace_field(
        document,
        fragment,
        "fragment",
        pure.project_ir_pure_text("zero"),
    )
    unknown_enum = _replace_field(
        document,
        fragment,
        "state",
        pure.project_ir_pure_enumeration("invented"),
    )
    negative = _replace_field(
        document,
        header,
        "node_start",
        pure.project_ir_pure_integer(-1),
    )
    out_of_range = _replace_field(
        document,
        header,
        "node_start",
        pure.project_ir_pure_integer(pure.PROJECT_IR_PURE_MAX_INTEGER + 1),
    )
    duplicate_header = replace(
        document,
        records=(document.records[0], *document.records),
    )
    reordered = list(document.records)
    reordered[fragment], reordered[node] = reordered[node], reordered[fragment]
    section_order = replace(document, records=tuple(reordered))

    last_node = max(
        position
        for position, record in enumerate(document.records)
        if record.kind == "node"
    )
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
    second_node = next(
        position
        for position in range(node + 1, len(document.records))
        if document.records[position].kind == "node"
    )
    first_node_ref = _field_value(document.records[node], "node").ref
    assert first_node_ref is not None
    duplicate_ref = _replace_field(
        document,
        second_node,
        "node",
        pure.project_ir_pure_ref(first_node_ref),
    )
    missing_ref = _replace_field(
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
    non_concrete_fragment = next(
        position
        for position, record in enumerate(document.records)
        if record.kind == "fragment"
        and _field_value(record, "state").text != "concrete"
    )
    invalid_state = _replace_field(
        document,
        non_concrete_fragment,
        "root",
        pure.project_ir_pure_ref(first_node_ref),
    )
    bad_topological = _replace_field(
        document,
        topological,
        "node",
        pure.project_ir_pure_ref(last_node_ref),
    )
    trailing = replace(
        document,
        records=(*document.records, document.records[fragment]),
    )
    missing_header = replace(document, records=document.records[1:])

    cases = (
        (pure.ProjectIRPureDocument(), pure.ProjectIRPureStatus.EMPTY_DOCUMENT),
        (missing_header, pure.ProjectIRPureStatus.MISSING_HEADER_RECORD),
        (bad_marker, pure.ProjectIRPureStatus.UNKNOWN_FORMAT_MARKER),
        (unknown_kind, pure.ProjectIRPureStatus.UNKNOWN_RECORD_KIND),
        (wrong_arity, pure.ProjectIRPureStatus.FIELD_ARITY_MISMATCH),
        (wrong_key, pure.ProjectIRPureStatus.FIELD_KEY_MISMATCH),
        (wrong_tag, pure.ProjectIRPureStatus.VALUE_TAG_MISMATCH),
        (unknown_enum, pure.ProjectIRPureStatus.UNKNOWN_ENUMERATION),
        (negative, pure.ProjectIRPureStatus.NEGATIVE_INTEGER),
        (out_of_range, pure.ProjectIRPureStatus.INTEGER_OUT_OF_RANGE),
        (duplicate_header, pure.ProjectIRPureStatus.DUPLICATE_SINGLETON_RECORD),
        (section_order, pure.ProjectIRPureStatus.SECTION_ORDER_VIOLATION),
        (non_dense, pure.ProjectIRPureStatus.NON_DENSE_REF_COORDINATES),
        (duplicate_ref, pure.ProjectIRPureStatus.DUPLICATE_REF),
        (missing_ref, pure.ProjectIRPureStatus.DANGLING_REF),
        (wrong_domain, pure.ProjectIRPureStatus.REF_DOMAIN_MISMATCH),
        (invalid_endpoint, pure.ProjectIRPureStatus.INVALID_ENDPOINT_RELATION),
        (invalid_state, pure.ProjectIRPureStatus.INVALID_FRAGMENT_STATE),
        (bad_topological, pure.ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE),
        (trailing, pure.ProjectIRPureStatus.TRAILING_RECORD),
    )
    for malformed, expected in cases:
        first = pure.evaluate_project_ir_document(malformed)
        second = pure.evaluate_project_ir_document(malformed)
        assert first.status is expected
        assert first == second
        assert first.canonical_bytes is None
        assert not hasattr(first, "message")


_DETERMINISM_PROBE = r"""
from pathlib import Path
import sys

from pietto._project import check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import build_project_ir_evaluation_context_stage
from pietto._project.project_ir_inspection import build_project_ir_inspection
from pietto._project.project_ir_verification import build_project_ir_analysis_bundle, verify_project_ir_stage

semantic = build_empty_project_semantic_result(check.check_project_parse_only(Path(sys.argv[1])))
facts = semantic.module_semantic_facts
attribution = semantic.module_attribution_facts
assert facts is not None and attribution is not None
plan = build_project_ir_project_plan(semantic_facts=facts, attribution=attribution, allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()))
stage = build_project_ir_evaluation_context_stage(plan)
bundle = build_project_ir_analysis_bundle(verify_project_ir_stage(stage))
product = build_project_ir_inspection(bundle)
print(product.canonical_bytes.decode("utf-8"), end="")
"""


def test_inspection_serialization_is_hash_seed_cwd_independent_and_public_zero_delta(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    _semantic_project(project_root)
    outputs = []
    for seed, cwd_name in (("1", "cwd-a"), ("977", "cwd-b")):
        cwd = tmp_path / cwd_name
        cwd.mkdir()
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        existing = environment.get("PYTHONPATH")
        source_root = str(REPO_ROOT / "src")
        environment["PYTHONPATH"] = (
            source_root if not existing else os.pathsep.join((source_root, existing))
        )
        completed = subprocess.run(
            (sys.executable, "-c", _DETERMINISM_PROBE, str(project_root)),
            cwd=cwd,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]
    assert str(tmp_path) not in outputs[0]
    assert "0x" not in outputs[0]
    assert outputs[0].startswith("header\tformat=e:pietto.project-ir-inspection.v1")

    assert not hasattr(pietto, "ProjectIRInspection")
    assert not hasattr(project_package, "ProjectIRInspection")
    assert tuple(item.name for item in fields(RelationIR)) == (
        "symbol",
        "name",
        "kind",
        "source",
        "filter",
        "projections",
        "row_schema",
        "span",
        "order_by",
        "limit",
        "group_keys",
        "result_predicate",
        "named_windows",
    )
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
        REPO_ROOT / "src/pietto/cli.py",
        REPO_ROOT / "src/pietto/ir/model.py",
        REPO_ROOT / "src/pietto/sql/relations.py",
        REPO_ROOT / "src/pietto/sql/mysql_relations.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "project_ir_inspection" not in text
        assert "project_ir_pure_boundary" not in text
        assert "ProjectIRInspection" not in text
    production = (REPO_ROOT / "src/pietto/_project/project_ir_inspection.py").read_text(
        encoding="utf-8"
    )
    assert "sha256" not in production
    assert "hashlib" not in production
    assert "deserial" not in production.lower()
