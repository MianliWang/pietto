from __future__ import annotations

import argparse
from copy import copy
from dataclasses import replace
from importlib.metadata import version
import json
from pathlib import Path
from typing import cast

from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import _declaration_identity
from pietto._project.project_ir_inspection import build_project_ir_inspection
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
)
from pietto._project.project_phase62_inspection import (
    build_project_phase62_inspection,
)
from pietto._project.project_phase62_verification import (
    build_project_phase62_analysis_bundle,
)
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockEntry,
    ProjectIRQueryBlockTerminal,
    ProjectIRReboundExistingOutput,
    ProjectIRReusedEffectiveOutput,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_inspection import (
    ProjectIRQueryBlockInspection,
    ProjectIRQueryBlockInspectionProduct,
    build_project_query_block_ir_inspection,
    query_project_query_block_active_roots,
    query_project_query_block_entries,
    query_project_query_block_outputs,
)
from pietto._project.project_query_block_ir_pure_boundary import (
    ProjectQueryBlockIRPortableRef,
    ProjectQueryBlockIRPortableRefDomain,
    ProjectQueryBlockIRPureDocument,
    ProjectQueryBlockIRPureRecord,
    ProjectQueryBlockIRPureTag,
    ProjectQueryBlockIRPureValue,
    ProjectQueryBlockIRRecordKind,
    evaluate_project_query_block_ir_document,
    project_query_block_ir_pure_ref,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockVerificationStatus,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)


OBSERVATION_FORMAT = "pietto.phase63-query-block-ir-differential.v1"
SEED_ENVIRONMENT = "PIETTO_PHASE63_SLICE15_AMBIENT"


MAIN_SOURCE = """shape AccountRow:
    id: Int not null
    metric: Int nullable
    unique account_key on id
shape EventRow:
    id: Int not null
    account_id: Int not null
    metric: Int nullable
    unique event_key on id
source accounts: AccountRow is postgres.table("accounts")
source events: EventRow is postgres.table("events")
relationship account_events:
    endpoint account: accounts
    endpoint event: events
    on account.id == event.account_id
query plain:
    from accounts
    select:
        id
query joined:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = accounts.id
        event_id = event.id
query downstream:
    from joined
    select:
        event_id
query grouped:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(event.metric)
query global:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
query qualified:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3
query filtered:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.id > 0
    select:
        event_id = event.id
query satisfying:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
    satisfying:
        event_id > 0 and total > 0
query hidden_qualify:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        row_number() window:
            order by:
                event.id
        <= 3
query ordered_limited:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    order by:
        event.id desc
    limit 1
query computed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        doubled = event.metric * 2
query key_drop:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        metric = event.metric
query mixed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.id > 0
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
        ranked = rank() window:
            order by:
                total
    satisfying:
        event_id > 0 and total > 0
    qualify:
        ranked <= 3
    order by:
        event_id desc
        ranked
    limit 5
query replay_selected:
    from accounts
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
query replay_full:
    from accounts
    where id > 0
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
    order by:
        id desc
        ranked
    limit 2
query rebound_one:
    from replay_selected
    select:
        id
query rebound_two:
    from rebound_one
    select:
        id
query qualified_events:
    from events
    select:
        id
        account_id
        metric
    qualify:
        row_number() window:
            order by:
                id
        <= 3
relationship account_qualified_events:
    endpoint account: accounts
    endpoint event: qualified_events
    on account.id == event.account_id
query stale_join:
    from accounts
    inner join qualified_events as event:
        from accounts
        via account_qualified_events: account -> event
    select:
        event_id = event.id
query downstream_stale:
    from stale_join
    select:
        event_id
shape DetailRow:
    id: Int not null
    event_id: Int not null
    unique detail_key on id
source details: DetailRow is postgres.table("details")
relationship event_details:
    endpoint event: events
    endpoint detail: details
    on event.id == detail.event_id
query multi_join:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    left join details as detail:
        from event
        via event_details: event -> detail
    select:
        account_id = accounts.id
        event_id = event.id
        detail_id = detail.id
query left_selected_hidden:
    from accounts
    left join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3 and row_number() window:
            order by:
                event.id
        <= 3
query window_base:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
query qualify_added:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3
query relation_order_added:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    order by:
        event.id desc
query limit_one:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit 1
query limit_two:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit 2
query left_joined:
    from accounts
    left join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = accounts.id
        event_id = event.id
query semantic_bad:
    from missing
    select:
        id
query semantic_bad_downstream:
    from semantic_bad
    select:
        id
"""


DISCONNECTED_SOURCE = """shape AuditRow:
    id: Int not null
    unique audit_key on id
source audit_rows: AuditRow is postgres.table("audit_rows")
query audit_result:
    from audit_rows
    select:
        id
"""


# Reviewed, checked-in semantic expectations. Portable records and bytes remain
# the actual cross-environment comparison authority.
SCENARIO_MANIFEST = (
    ("accounts", "reused", ()),
    ("events", "reused", ()),
    ("plain", "reused", ()),
    ("joined", "completed", ("final_projection",)),
    ("downstream", "completed", ("relation_input", "final_projection")),
    ("grouped", "completed", ("group_aggregate", "final_projection")),
    ("global", "completed", ("group_aggregate", "final_projection")),
    (
        "qualified",
        "completed",
        ("window_evaluation", "qualify", "final_projection"),
    ),
    ("filtered", "completed", ("row_filter", "final_projection")),
    (
        "satisfying",
        "completed",
        ("group_aggregate", "result_filter", "final_projection"),
    ),
    (
        "hidden_qualify",
        "completed",
        ("window_evaluation", "qualify", "final_projection"),
    ),
    (
        "ordered_limited",
        "completed",
        ("final_projection", "relation_ordering", "limit"),
    ),
    ("computed", "completed", ("final_projection",)),
    ("key_drop", "completed", ("final_projection",)),
    (
        "mixed",
        "completed",
        (
            "row_filter",
            "group_aggregate",
            "result_filter",
            "window_evaluation",
            "qualify",
            "final_projection",
            "relation_ordering",
            "limit",
        ),
    ),
    (
        "replay_selected",
        "completed",
        ("relation_input", "window_evaluation", "qualify", "final_projection"),
    ),
    (
        "replay_full",
        "completed",
        (
            "relation_input",
            "row_filter",
            "window_evaluation",
            "qualify",
            "final_projection",
            "relation_ordering",
            "limit",
        ),
    ),
    ("rebound_one", "rebound", ("relation_input", "final_projection")),
    ("rebound_two", "rebound", ("relation_input", "final_projection")),
    (
        "qualified_events",
        "completed",
        ("relation_input", "window_evaluation", "qualify", "final_projection"),
    ),
    ("stale_join", "terminal", ()),
    ("downstream_stale", "terminal", ()),
    ("details", "reused", ()),
    ("multi_join", "completed", ("final_projection",)),
    (
        "left_selected_hidden",
        "completed",
        ("window_evaluation", "qualify", "final_projection"),
    ),
    ("window_base", "completed", ("window_evaluation", "final_projection")),
    (
        "qualify_added",
        "completed",
        ("window_evaluation", "qualify", "final_projection"),
    ),
    (
        "relation_order_added",
        "completed",
        ("window_evaluation", "final_projection", "relation_ordering"),
    ),
    ("limit_one", "completed", ("final_projection", "limit")),
    ("limit_two", "completed", ("final_projection", "limit")),
    ("left_joined", "completed", ("final_projection",)),
    ("semantic_bad", "terminal", ()),
    ("semantic_bad_downstream", "terminal", ()),
    ("audit_rows", "reused", ()),
    ("audit_result", "reused", ()),
)


def _write_project(root: Path, *, reverse_creation: bool) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    files = (
        ("main.pietto", MAIN_SOURCE),
        ("z_disconnected.pietto", DISCONNECTED_SOURCE),
    )
    for name, source in tuple(reversed(files)) if reverse_creation else files:
        (root / name).write_text(source, encoding="utf-8")
    return root


def _construction(
    root: Path,
    *,
    reverse_creation: bool,
) -> tuple[
    ProjectConcreteCompletedSemanticResult,
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockInspectionProduct,
    bytes,
    bytes,
]:
    parse_result = check_project_parse_only(
        _write_project(root, reverse_creation=reverse_creation)
    )
    if not parse_result.ok:
        raise AssertionError("Reviewed Phase-63 corpus must parse.")
    semantic_result = build_empty_project_semantic_result(parse_result)
    completed = build_project_completed_semantic_result(semantic_result)
    if type(completed) is not ProjectConcreteCompletedSemanticResult:
        raise AssertionError("Reviewed Phase-63 corpus must complete.")
    snapshot = build_project_query_block_ir(completed)
    verification = verify_project_query_block_ir(snapshot)
    if verification.status is not ProjectIRQueryBlockVerificationStatus.VERIFIED:
        raise AssertionError("Reviewed Slice-14 snapshot must verify.")
    bundle = build_project_query_block_ir_analysis_bundle(verification)
    product = build_project_query_block_ir_inspection(bundle)

    phase61_bundle = build_project_ir_analysis_bundle(
        completed.verification.base_verification
    )
    phase61_product = build_project_ir_inspection(phase61_bundle)
    phase62_bundle = build_project_phase62_analysis_bundle(completed.verification)
    phase62_product = build_project_phase62_inspection(phase62_bundle)
    if (
        phase61_product.inspection.stage.project_plan
        is not product.inspection.base_plan
        or phase62_product.inspection.root is not product.inspection.phase62_root
    ):
        raise AssertionError("Historical inspections must retain the exact roots.")
    return (
        completed,
        bundle,
        product,
        phase61_product.canonical_bytes,
        phase62_product.canonical_bytes,
    )


def _entry(
    inspection: ProjectIRQueryBlockInspection,
    name: str,
) -> ProjectIRQueryBlockEntry:
    matches = tuple(
        entry
        for entry in inspection.entries
        if entry.owner.identity.declared_name == name
    )
    if len(matches) != 1:
        raise AssertionError("Reviewed owner name must have one occurrence.")
    return matches[0]


def _variant(entry: ProjectIRQueryBlockEntry) -> str:
    if type(entry) is ProjectIRReusedEffectiveOutput:
        return "reused"
    if type(entry) is ProjectIRReboundExistingOutput:
        return "rebound"
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return "completed"
    if type(entry) is ProjectIRQueryBlockTerminal:
        return "terminal"
    raise AssertionError("Unexpected Slice-14 entry.")


def _operator_kinds(entry: ProjectIRQueryBlockEntry) -> tuple[str, ...]:
    if type(entry) is ProjectIRReboundExistingOutput:
        return tuple(
            operator.kind.value
            for operator in entry.rebuilt_fragment.logical_stage.operators
        )
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return tuple(operator.kind.value for operator in entry.operators)
    return ()


def _manifest(inspection: ProjectIRQueryBlockInspection) -> tuple[object, ...]:
    return tuple(
        (
            name,
            _variant(_entry(inspection, name)),
            _operator_kinds(_entry(inspection, name)),
        )
        for name, _expected_variant, _expected_operators in SCENARIO_MANIFEST
    )


def _ref_value(ref: object) -> object:
    if type(ref) is ProjectQueryBlockIRPortableRef:
        typed = cast(ProjectQueryBlockIRPortableRef, ref)
        return [typed.domain.value, typed.position]
    raise TypeError("Portable observation requires one exact ref.")


def _pure_value(value: ProjectQueryBlockIRPureValue) -> object:
    if value.tag is ProjectQueryBlockIRPureTag.ABSENT:
        payload: object = None
    elif value.tag is ProjectQueryBlockIRPureTag.TEXT:
        payload = value.text
    elif value.tag is ProjectQueryBlockIRPureTag.INTEGER:
        payload = value.integer
    elif value.tag is ProjectQueryBlockIRPureTag.BOOLEAN:
        payload = value.boolean
    elif value.tag is ProjectQueryBlockIRPureTag.ENUMERATION:
        payload = value.enumeration
    elif value.tag is ProjectQueryBlockIRPureTag.REF:
        payload = _ref_value(value.ref)
    elif value.tag is ProjectQueryBlockIRPureTag.REFS:
        payload = [_ref_value(ref) for ref in value.refs]
    elif value.tag is ProjectQueryBlockIRPureTag.TEXTS:
        payload = list(value.texts)
    elif value.tag is ProjectQueryBlockIRPureTag.INTEGERS:
        payload = list(value.integers)
    else:
        payload = list(value.enumerations)
    return [value.tag.value, payload]


def _portable_records(document: ProjectQueryBlockIRPureDocument) -> list[object]:
    return [
        [
            record.kind.value,
            [[field.key, _pure_value(field.value)] for field in record.fields],
        ]
        for record in document.records
    ]


def _active_entry(
    entry: ProjectIRQueryBlockEntry,
) -> (
    ProjectIRReusedEffectiveOutput
    | ProjectIRReboundExistingOutput
    | ProjectIRCompletedQueryBlockOutput
):
    if type(entry) is ProjectIRReusedEffectiveOutput:
        return entry
    if type(entry) is ProjectIRReboundExistingOutput:
        return entry
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry
    raise AssertionError("Expected one concrete Slice-14 entry.")


def _property_signature(entry: ProjectIRQueryBlockEntry) -> object:
    concrete = _active_entry(entry)
    relational = concrete.active_properties.relational
    return [
        [
            [member.field_position for member in value_class.members]
            for value_class in relational.value_classes
        ],
        [
            [
                [relational.value_classes.index(item) for item in key.determinants],
                key.strength.value,
            ]
            for key in relational.keys
        ],
        [
            [
                [relational.value_classes.index(item) for item in fd.determinants],
                [relational.value_classes.index(item) for item in fd.dependents],
                fd.strength.value,
            ]
            for fd in relational.fds
        ],
        relational.grain.state.value,
        [factor.identity.kind.value for factor in relational.grain.factors],
        [factor.kind.value for factor in relational.grain.active],
        [field.effective_nullability.value for field in relational.fields],
        type(concrete.active_properties.ordering).__name__
        if concrete.active_properties.ordering is not None
        else None,
    ]


def _selected_window_summary(
    entry: ProjectIRCompletedQueryBlockOutput,
) -> tuple[int, bool]:
    selected = tuple(
        scalar for scalar in entry.scalar_outputs if scalar.final_identity is None
    )
    singleton = all(
        any(
            len(value_class.members) == 1
            and value_class.members[0].field_position == scalar.field_position
            for properties in entry.row_properties
            if properties.output is scalar.row_output
            for value_class in properties.relational.value_classes
        )
        for scalar in selected
    )
    return len(selected), singleton


def _query_observation(
    inspection: ProjectIRQueryBlockInspection,
    *,
    reverse: bool,
) -> tuple[object, ...]:
    owners = tuple(reversed(inspection.owners)) if reverse else inspection.owners
    buckets: dict[str, object] = {}
    for owner in owners:
        identity = _declaration_identity(owner)
        entries = query_project_query_block_entries(inspection, identity)
        active = query_project_query_block_active_roots(inspection, identity)
        buckets[owner.identity.declared_name] = [
            len(entries),
            len(active),
            [pair[0].occurrence.ref.position for pair in active],
        ]
    return tuple(buckets[owner.identity.declared_name] for owner in inspection.owners)


def _metamorphics(inspection: ProjectIRQueryBlockInspection) -> dict[str, object]:
    hidden = _active_entry(_entry(inspection, "hidden_qualify"))
    selected = _active_entry(_entry(inspection, "qualified"))
    selected_hidden = _active_entry(_entry(inspection, "left_selected_hidden"))
    if not all(
        type(entry) is ProjectIRCompletedQueryBlockOutput
        for entry in (hidden, selected, selected_hidden)
    ):
        raise AssertionError("Window scenarios require completed entries.")
    hidden = cast(ProjectIRCompletedQueryBlockOutput, hidden)
    selected = cast(ProjectIRCompletedQueryBlockOutput, selected)
    selected_hidden = cast(ProjectIRCompletedQueryBlockOutput, selected_hidden)

    window_base = _active_entry(_entry(inspection, "window_base"))
    qualify_added = _active_entry(_entry(inspection, "qualify_added"))
    relation_order = _active_entry(_entry(inspection, "relation_order_added"))
    limit_one = _active_entry(_entry(inspection, "limit_one"))
    limit_two = _active_entry(_entry(inspection, "limit_two"))
    grouped = _active_entry(_entry(inspection, "grouped"))
    global_entry = _active_entry(_entry(inspection, "global"))
    joined = _active_entry(_entry(inspection, "joined"))
    left_joined = _active_entry(_entry(inspection, "left_joined"))
    multi_join = _active_entry(_entry(inspection, "multi_join"))
    replay = _active_entry(_entry(inspection, "replay_selected"))
    rebound_one = _active_entry(_entry(inspection, "rebound_one"))
    rebound_two = _active_entry(_entry(inspection, "rebound_two"))
    plain = _active_entry(_entry(inspection, "plain"))
    stale_join = cast(ProjectIRQueryBlockTerminal, _entry(inspection, "stale_join"))
    if (
        type(replay) is not ProjectIRCompletedQueryBlockOutput
        or replay.relation_input is None
        or type(rebound_one) is not ProjectIRReboundExistingOutput
        or type(rebound_two) is not ProjectIRReboundExistingOutput
        or type(plain) is not ProjectIRReusedEffectiveOutput
        or type(multi_join) is not ProjectIRCompletedQueryBlockOutput
    ):
        raise AssertionError("Reuse/rebound scenarios require exact variants.")

    selected_count, selected_singletons = _selected_window_summary(selected)
    hidden_selected_count, _ = _selected_window_summary(hidden)
    combined_selected_count, _ = _selected_window_summary(selected_hidden)
    active = _active_entry(_entry(inspection, "ordered_limited"))
    observed_with_extra = (
        *cast(ProjectIRCompletedQueryBlockOutput, active).row_outputs,
        selected.row_outputs[0],
    )
    observed_reversed = tuple(reversed(observed_with_extra))

    return {
        "active_root_invariance": [
            active.active_output.occurrence.ref.position,
            active.active_output.occurrence.ref.position,
            active.active_output.occurrence.ref.position,
            len(observed_with_extra),
            len(observed_reversed),
        ],
        "selected_hidden": {
            "selected": [
                _operator_kinds(selected).count("window_evaluation"),
                selected_count,
                selected_singletons,
            ],
            "hidden": [
                _operator_kinds(hidden).count("window_evaluation"),
                hidden_selected_count,
                sum(
                    len(item.hidden)
                    for item in inspection.window_evidence
                    if item.completed_output is hidden.semantic_entry
                ),
                _operator_kinds(hidden),
            ],
            "selected_and_hidden": [
                combined_selected_count,
                sum(
                    len(item.hidden)
                    for item in inspection.window_evidence
                    if item.completed_output is selected_hidden.semantic_entry
                ),
            ],
        },
        "qualify": [
            _operator_kinds(window_base),
            _operator_kinds(qualify_added),
            _property_signature(window_base) == _property_signature(qualify_added),
        ],
        "window_vs_relation_order": [
            type(window_base.active_properties.ordering).__name__
            if window_base.active_properties.ordering is not None
            else None,
            type(relation_order.active_properties.ordering).__name__
            if relation_order.active_properties.ordering is not None
            else None,
        ],
        "limit": [
            limit_one.active_properties.row_count_upper_bound,
            limit_two.active_properties.row_count_upper_bound,
            _property_signature(limit_one) == _property_signature(limit_two),
            limit_one.active_properties.relational.grain.state.value,
            limit_two.active_properties.relational.grain.state.value,
        ],
        "grouped_global": [
            grouped.active_properties.relational.grain.state.value,
            [
                factor.kind.value
                for factor in grouped.active_properties.relational.grain.active
            ],
            global_entry.active_properties.relational.grain.state.value,
            [
                factor.kind.value
                for factor in global_entry.active_properties.relational.grain.active
            ],
            len(global_entry.active_properties.relational.keys),
        ],
        "downstream": [
            rebound_one.relation_input.use.output is replay.active_output.occurrence,
            rebound_two.relation_input.use.output
            is rebound_one.active_output.occurrence,
        ],
        "reuse_rebound": [
            type(plain).__name__,
            plain.starting_allocation is plain.ending_allocation,
            type(rebound_one).__name__,
            rebound_one.rebuilt_fragment is not rebound_one.semantic_entry.fragment,
        ],
        "effective_join": [
            stale_join.reason.value,
            cast(
                ProjectIRQueryBlockTerminal, _entry(inspection, "downstream_stale")
            ).reason.value,
            stale_join.starting_allocation is stale_join.ending_allocation,
            not any(
                node.anchor.identity == _declaration_identity(stale_join.owner)
                for node in inspection.slice14_nodes
            ),
        ],
        "inner_left": [
            [
                field.effective_nullability.value
                for field in joined.active_properties.relational.fields
            ],
            [
                field.effective_nullability.value
                for field in left_joined.active_properties.relational.fields
            ],
            [
                len(field.nulling_joins)
                for field in cast(
                    ProjectIRCompletedQueryBlockOutput, left_joined
                ).active_output.row_shape.fields
            ],
        ],
        "multi_join": [
            len(multi_join.source_properties.output.row_shape.fields),
            [
                len(field.nulling_joins)
                for field in multi_join.active_output.row_shape.fields
            ],
        ],
        "duplicate_intermediate_names": [
            len(multi_join.source_properties.output.row_shape.fields),
            len(
                {
                    field.evidence.name
                    for field in multi_join.source_properties.output.row_shape.fields
                }
            ),
        ],
    }


def _replace_record(
    document: ProjectQueryBlockIRPureDocument,
    position: int,
    replacement: ProjectQueryBlockIRPureRecord,
) -> ProjectQueryBlockIRPureDocument:
    return replace(
        document,
        records=(
            *document.records[:position],
            replacement,
            *document.records[position + 1 :],
        ),
    )


def _negative_observation(
    primary: ProjectIRQueryBlockInspectionProduct,
    foreign: ProjectIRQueryBlockInspectionProduct,
    bundle: ProjectIRQueryBlockAnalysisBundle,
) -> dict[str, object]:
    invalid_verification = copy(bundle.verification)
    object.__setattr__(
        invalid_verification,
        "status",
        ProjectIRQueryBlockVerificationStatus.INVALID,
    )
    invalid_bundle = copy(bundle)
    object.__setattr__(invalid_bundle, "verification", invalid_verification)
    try:
        build_project_query_block_ir_inspection(invalid_bundle)
    except ValueError:
        non_verified = "rejected"
    else:
        non_verified = "accepted"

    try:
        query_project_query_block_outputs(
            primary.inspection,
            foreign.inspection.combined_outputs[0].ref,
        )
    except ValueError:
        cross_snapshot = "rejected"
    else:
        cross_snapshot = "accepted"

    document = primary.document
    unknown = replace(document, format_marker="untrusted\nformat")
    node_position = next(
        position
        for position, record in enumerate(document.records)
        if record.kind is ProjectQueryBlockIRRecordKind.NODE
    )
    owner_position = next(
        position
        for position, record in enumerate(document.records)
        if record.kind is ProjectQueryBlockIRRecordKind.OWNER_ENTRY
    )
    section_order = replace(
        document,
        records=(
            *document.records[:owner_position],
            document.records[node_position],
            *document.records[owner_position + 1 : node_position],
            document.records[owner_position],
            *document.records[node_position + 1 :],
        ),
    )
    use_position = next(
        position
        for position, record in enumerate(document.records)
        if record.kind is ProjectQueryBlockIRRecordKind.USE
    )
    use = document.records[use_position]
    output_field_position = next(
        position for position, field in enumerate(use.fields) if field.key == "output"
    )
    dangling_use = replace(
        use,
        fields=(
            *use.fields[:output_field_position],
            replace(
                use.fields[output_field_position],
                value=project_query_block_ir_pure_ref(
                    ProjectQueryBlockIRPortableRef(
                        domain=ProjectQueryBlockIRPortableRefDomain.OUTPUT_VALUE,
                        position=10**6,
                    )
                ),
            ),
            *use.fields[output_field_position + 1 :],
        ),
    )
    dangling = _replace_record(document, use_position, dangling_use)

    pure_rejections = []
    for label, malformed in (
        ("unknown_format", unknown),
        ("section_order", section_order),
        ("dangling_ref", dangling),
    ):
        result = evaluate_project_query_block_ir_document(malformed)
        pure_rejections.append(
            [label, result.status.value, result.record_position, result.field_position]
        )
    return {
        "non_verified_admission": non_verified,
        "cross_snapshot_ref": cross_snapshot,
        "terminals": [
            [
                name,
                cast(
                    ProjectIRQueryBlockTerminal, _entry(primary.inspection, name)
                ).reason.value,
            ]
            for name in ("semantic_bad", "downstream_stale", "stale_join")
        ],
        "pure_rejections": pure_rejections,
    }


def observation(workspace: Path) -> dict[str, object]:
    first = _construction(workspace / "primary-normal", reverse_creation=False)
    second = _construction(workspace / "primary-reverse", reverse_creation=True)
    _, first_bundle, first_product, first_phase61, first_phase62 = first
    _, second_bundle, second_product, second_phase61, second_phase62 = second
    first_manifest = _manifest(first_product.inspection)
    second_manifest = _manifest(second_product.inspection)
    if first_manifest != SCENARIO_MANIFEST or second_manifest != SCENARIO_MANIFEST:
        raise AssertionError("Reviewed Phase-63 manifest drifted.")
    normal_queries = _query_observation(first_product.inspection, reverse=False)
    reverse_queries = _query_observation(first_product.inspection, reverse=True)
    if (
        first_product.canonical_bytes != second_product.canonical_bytes
        or first_product.document != second_product.document
        or first_phase61 != second_phase61
        or first_phase62 != second_phase62
        or normal_queries != reverse_queries
    ):
        raise AssertionError("Authored/order differential observation drifted.")
    identities_distinct = all(
        left is not right
        for left, right in zip(
            first_product.inspection.entries,
            second_product.inspection.entries,
            strict=True,
        )
    )
    return {
        "observation_format": OBSERVATION_FORMAT,
        "package_version": version("pietto"),
        "runtime_identities_distinct": identities_distinct,
        "scenario_manifest": first_manifest,
        "query_order_invariant": normal_queries == reverse_queries,
        "file_creation_order_invariant": first_product.canonical_bytes
        == second_product.canonical_bytes,
        "continuity": [
            first_product.inspection.analysis_bundle is first_bundle,
            first_product.inspection.root is first_bundle.root,
            first_product.inspection.completed is first_bundle.root.completed,
            first_product.inspection.phase62_root
            is first_bundle.root.completed.verification.root,
            first_product.inspection.base_plan
            is first_bundle.root.completed.verification.root.evaluation.project_plan,
        ],
        "portable_records": _portable_records(first_product.document),
        "canonical_bytes": first_product.canonical_bytes.decode("utf-8"),
        "phase61_marker": first_phase61.decode("utf-8").split("\t", 2)[1],
        "phase61_canonical_bytes": first_phase61.decode("utf-8"),
        "phase62_marker": first_phase62.decode("utf-8").split("\t", 2)[1],
        "phase62_canonical_bytes": first_phase62.decode("utf-8"),
        "metamorphics": _metamorphics(first_product.inspection),
        "negative": _negative_observation(first_product, second_product, first_bundle),
        "second_bundle_distinct": second_bundle is not first_bundle,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args()
    result = observation(arguments.workspace)
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
