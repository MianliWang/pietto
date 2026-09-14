"""Real-source selected-plan observations through the existing process matrix."""

from __future__ import annotations

import argparse
from copy import copy
from dataclasses import replace
import json
from pathlib import Path
import sys

from _pietto_phase64_flat_ir_differential_probe import CONTROL, FD_SOURCE
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
    with_project_single_match_requests,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchRequest,
    ProjectSingleMatchScope,
)
from pietto._project import project_sql_plan as plans
from pietto._project import project_sql_plan_literals as literals
from pietto._project import project_sql_plan_portable as portable
from pietto._project import project_sql_plan_pure_boundary as pure
from pietto._project import project_sql_plan_target_assessment as targets
from pietto._project import project_sql_plan_portable_schema as schema
from pietto._project import project_sql_plan_requirements as reports
from pietto._project import project_sql_plan_source_maps as maps
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto.ast_nodes import DottedNameExpr, LiteralExpr
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto.semantic.capability_profiles import (
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    CapabilityProfileReference,
    CapabilityProfileIdentity,
    CapabilityProfileSchemaVersion,
    CapabilityProfileKind,
    StaticCapabilityProfile,
    CapabilityProfileFactOccurrence,
)
from pietto.semantic.capability_facts import (
    CapabilityKey,
    CapabilityDomain,
    CapabilitySupport,
)
from pietto.semantic.capability_inventory import _LOGICAL_TYPE_FACTS

__all__ = ("observation", "render")
SEED_ENVIRONMENT = "PIETTO_PHASE65_SLICE14_AMBIENT"

BOUND_SOURCE = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    let:
        added = id + 1
    where added > 0
    select:
        added
        flag = true
        floating = 1.25
        negative_zero = -0.0
        text = "https://example.invalid/0x/source/😀"
        large = 123456789012345678901234567890123456789012345678901234567890
"""
SET_SOURCE = """shape Row:
    id: Decimal(10, 2) nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
table visible:
    from lhs
    select distinct:
        id
    order by:
        id
    limit 2
table combined:
    union all:
        from visible
        from rhs
        from visible
query result:
    except distinct:
        from combined
        from visible
"""
STAGED_SOURCE = """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    group by:
        id
    select:
        total = count()
        w = rank() window:
            order by:
                total
    satisfying:
        total > 0
    qualify:
        w <= 3
    order by:
        total
    limit 2
"""
ORIGINAL_CORPUS = (
    ("minimal", CONTROL, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
    ("bound", BOUND_SOURCE, literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS),
    ("shared_set", SET_SOURCE, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
    ("staged", STAGED_SOURCE, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
    ("hidden_order", FD_SOURCE, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
)


ROW_SHARED = (
    CONTROL.split("query result:")[0]
    + """query result:
    from rows
    let:
        a = 1
        b = 1.0
        c = true
        d = "text"
    where true and 1 == 1 and 1.0 > 0.0 and "x" == "x"
    select:
        n = -3
        z = -0.0
        f = 1.25
        t = "é\\n😀"
        flag = false
        huge = 123456789012345678901234567890123456789
        first = a
        again = a
"""
)
JOIN_PREFIX = """shape Row:
    id: Int not null
    key: Int nullable
    allow_any: Bool nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
"""


def join_source(kind, predicate="true", *, via="", tail=""):
    condition = "" if kind == "cross" else f"        on {predicate}\n"
    return (
        JOIN_PREFIX
        + f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
{via}{condition}{tail}    select:
        id = lhs.id
"""
    )


def path_source(all_unique):
    unique = "    unique key on id\n" if all_unique else ""
    return f"""shape LeftRow:
    id: Int not null
{unique}shape RightRow:
    id: Int not null
    unique key on id
source lhs: LeftRow is postgres.table("lhs")
source rhs: RightRow is postgres.table("rhs")
relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
query result:
    from lhs
    inner join lhs as r:
        from lhs
        via link: l -> r
        via link: r -> l
    select:
        id = lhs.id
"""


def group_source(visible=""):
    return (
        """shape Row:
    id: Int not null
    key: Int nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
query result:
    from lhs
    left join rhs as r:
        from lhs
        on lhs.id == r.id
    group by:
        lhs.id
        r.id
    select:
"""
        + visible
        + "        total = count()\n"
    )


ORDINARY_PREFIX = """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
"""
GLOBAL_EMPTY = (
    ORDINARY_PREFIX
    + """query result:
    from rows
    where false
    select:
        rows = count()
        fields = count(value)
        total = sum(value)
"""
)
GROUPED_SATISFYING = (
    ORDINARY_PREFIX
    + """query result:
    from rows
    let:
        key = id
        amount = value + 1
    where false
    group by:
        key
    select:
        total = sum(amount)
    satisfying:
        total > 0 and sum(amount) > 1 and total < 10
"""
)
AGGREGATE_RISKS = (
    group_source()
    .replace(
        "    key: Int nullable\n",
        "    key: Int nullable\n    label: Text nullable\n    unique row_key on id\n",
    )
    .replace(
        "    group by:\n        lhs.id\n        r.id\n",
        """    let:
        group_value = lhs.id
        amount = r.key + 1
    where lhs.id > 0
    group by:
        group_value
""",
    )
    .replace(
        "        total = count()\n",
        """        row_count = count()
        field_count = count(r.id)
        distinct_labels = count_distinct(r.label)
        total = sum(amount)
        average = avg(amount)
        minimum = min(r.key)
        maximum = max(r.key)
        repeated_total = sum(amount)
    satisfying:
        total > 0 and total > 1 and total < 10
""",
    )
)
WINDOW_RANK_NAVIGATION = (
    ORDINARY_PREFIX
    + "query result:\n    from rows\n    select:\n        id\n"
    + "".join(
        f"        {name} = {call} window:\n            order by:\n                id desc\n"
        for name, call in (
            ("numbered", "row_number()"),
            ("ranked", "rank()"),
            ("dense", "dense_rank()"),
            ("percent", "percent_rank()"),
            ("distribution", "cume_dist()"),
            ("bucket", "ntile(3)"),
            ("previous", "lag(value, 2, 0)"),
            ("following", "lead(value, 0, value)"),
        )
    )
)
WINDOW_VALUE_NAMED = (
    ORDINARY_PREFIX
    + """query result:
    from rows
    select:
        id
        first = first_value(value) window composed
        again = last_value(value) window composed
        last = last_value(value) window:
            order by:
                id desc
            range between unbounded preceding and current row
        nth = nth_value(value, 2) from last ignore nulls window:
            order by:
                id desc
            groups between 1 preceding and current row exclude current row
    window composed = base
    window base:
        order by:
            id desc
        rows between unbounded preceding and current row
"""
)
MIXED_QUALIFY = (
    ORDINARY_PREFIX
    + """query result:
    from rows
    select:
        id
        w = row_number() window:
            order by:
                id
    qualify:
        row_number() window:
            order by:
                id
        <= 3 and w <= 2
"""
)
HIDDEN_DISTINCT = """shape Row:
    id: Int not null
    other: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    select distinct:
        constant = 1
    qualify:
        lag(rows.id, 1, rows.other) window:
            partition by:
                rows.other
            order by:
                rows.id
        > 0
    limit 0
"""
SET_FORMS = """type Base = Decimal(10, 2)
type Money = Base
shape Left:
    id: Money not null
shape Right:
    other: Money nullable
source lhs: Left is postgres.table("lhs")
source rhs: Right is postgres.table("rhs")
table united:
    union distinct:
        from lhs
        from rhs
table intersect_all:
    intersect all:
        from united
        from lhs
table intersect_distinct:
    intersect distinct:
        from intersect_all
        from rhs
table except_all:
    except all:
        from intersect_distinct
        from rhs
        from lhs
query result:
    except distinct:
        from except_all
        from united
"""
SET_FLOAT = """shape Left:
    id: Float not null
shape Right:
    other: Float nullable
source lhs: Left is postgres.table("lhs")
source rhs: Right is postgres.table("rhs")
query result:
    union all:
        from lhs
        from rhs
"""
SHARING_DEPTH12 = (
    CONTROL.replace("query result:", "table p0:").replace(
        "        id\n", "        id = 17\n"
    )
    + "".join(
        f"table p{i}:\n    union all:\n        from p{i - 1}\n        from p{i - 1}\n"
        for i in range(1, 13)
    )
    + "query result:\n    from p12\n    select:\n        id\n"
)
LIMIT_HEAD = (
    CONTROL.replace("query result:", "table bounded:")
    + "    order by:\n        id\n    limit 1\n"
)
LIMIT_CONSUMER = (
    "query result:\n    from bounded\n    where id > 0\n    select:\n        id\n"
)
IMPORTED_PRODUCER = (
    CONTROL.replace("query result:", "table shared:") + "export:\n    table shared\n"
)
IMPORTED_REEXPORT = (
    ("producer.pietto", IMPORTED_PRODUCER),
    ("other.pietto", IMPORTED_PRODUCER),
    (
        "facade.pietto",
        'import "producer.pietto":\n    table shared as public\nexport:\n    table public\n',
    ),
    (
        "main.pietto",
        """import "facade.pietto":
    table public as a
import "other.pietto":
    table shared as b
shape Local:
    id: Int not null
source extra: Local is mysql.table("extra")
query result:
    from a
    cross join a as again:
        from a
    cross join b as second:
        from a
    cross join extra as third:
        from a
    select:
        first = a.id
        repeated = again.id
        second = second.id
        third = third.id
""",
    ),
)
P = literals.ProjectSQLLiteralPolicy
CORPUS = (
    *ORIGINAL_CORPUS,
    ("row_shared", ROW_SHARED, P.BIND_SAFE_LITERALS),
    (
        "table_mysql",
        CONTROL.replace("postgres.table", "mysql.table").replace(
            "query result:", "table result:"
        ),
        P.PRESERVE_LITERALS,
    ),
    ("imported_reexport", IMPORTED_REEXPORT, P.BIND_SAFE_LITERALS),
    ("join_cross", join_source("cross"), P.PRESERVE_LITERALS),
    ("join_right", join_source("right"), P.BIND_SAFE_LITERALS),
    ("join_semi", join_source("semi"), P.BIND_SAFE_LITERALS),
    ("join_anti", join_source("anti"), P.PRESERVE_LITERALS),
    (
        "join_refinement",
        join_source(
            "inner",
            "r.key > 0",
            via="        via link: l -> r\n",
            tail="    where lhs.id > 0\n",
        ).replace(
            "    allow_any: Bool nullable\n",
            "    allow_any: Bool nullable\n    unique row_key on id\n",
        ),
        P.BIND_SAFE_LITERALS,
    ),
    (
        "join_accumulated",
        join_source(
            "left",
            tail="    full join rhs as last:\n        from lhs\n        on r.id == last.id\n",
        ),
        P.PRESERVE_LITERALS,
    ),
    (
        "proof_right_limit",
        JOIN_PREFIX
        + "table right_named:\n    from rhs\n    select:\n        id\n    limit 1\nquery result:\n    from lhs\n    inner join right_named as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n",
        P.BIND_SAFE_LITERALS,
    ),
    (
        "proof_right_global",
        join_source("inner", "lhs.id == r.id")
        .replace("query result:", "table upstream:")
        .replace("id = lhs.id", "total = count()")
        + "query result:\n    from lhs\n    semi join upstream as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n",
        P.PRESERVE_LITERALS,
    ),
    ("path_complete", path_source(True), P.PRESERVE_LITERALS),
    ("path_partial", path_source(False), P.BIND_SAFE_LITERALS),
    ("global_empty", GLOBAL_EMPTY, P.PRESERVE_LITERALS),
    ("group_hidden", group_source(), P.PRESERVE_LITERALS),
    ("group_partial", group_source("        left_id = lhs.id\n"), P.BIND_SAFE_LITERALS),
    ("grouped_satisfying", GROUPED_SATISFYING, P.BIND_SAFE_LITERALS),
    ("aggregate_risks", AGGREGATE_RISKS, P.PRESERVE_LITERALS),
    ("window_rank_navigation", WINDOW_RANK_NAVIGATION, P.BIND_SAFE_LITERALS),
    ("window_value_named", WINDOW_VALUE_NAMED, P.PRESERVE_LITERALS),
    ("mixed_qualify", MIXED_QUALIFY, P.BIND_SAFE_LITERALS),
    ("hidden_distinct", HIDDEN_DISTINCT, P.BIND_SAFE_LITERALS),
    ("set_forms", SET_FORMS, P.PRESERVE_LITERALS),
    ("set_float", SET_FLOAT, P.BIND_SAFE_LITERALS),
    ("sharing_depth12", SHARING_DEPTH12, P.BIND_SAFE_LITERALS),
    ("limit_before_filter", LIMIT_HEAD + LIMIT_CONSUMER, P.BIND_SAFE_LITERALS),
    (
        "filter_before_limit",
        LIMIT_HEAD.replace("    select:", "    where id > 0\n    select:")
        + LIMIT_CONSUMER.replace("    where id > 0\n", ""),
        P.BIND_SAFE_LITERALS,
    ),
    *(
        ("target_" + mode, CONTROL, P.PRESERVE_LITERALS)
        for mode in ("omitted", "applicable", "mismatch", "conflict", "residual")
    ),
)
REQUEST_MODES = {
    "join_right": "direct",
    "join_semi": "direct",
    "join_anti": "direct",
    "join_refinement": "direct",
    "proof_right_limit": "direct",
    "proof_right_global": "result_direct",
    "path_complete": "path",
    "path_partial": "path",
}


def _completed(workspace: Path, source):
    workspace.mkdir(parents=True)
    (workspace / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    files = (("main.pietto", source),) if isinstance(source, str) else source
    for name, text in files:
        (workspace / name).write_text(text, encoding="utf-8")
    parsed = check_project_parse_only(workspace)
    assert parsed.ok, parsed.diagnostics
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    return completed


def construction(workspace: Path, source, policy, *, requests=None):
    completed = _completed(workspace, source)
    assert completed.ok, completed.diagnostics
    if requests is not None:
        conditions = completed.roots.join_conditions.entries
        if requests == "path":
            (condition,) = conditions
            path = condition.effective_use.path
            assert path is not None and len(path.steps) == 2
            request = ProjectSingleMatchRequest(
                owner=condition.use.owner, use=condition.use, path=path
            )
            selected_requests = tuple(
                replace(request, scope=ProjectSingleMatchScope.PATH_HOP, hop=hop)
                for hop in path.steps
            ) + (replace(request, scope=ProjectSingleMatchScope.WHOLE_PATH),)
        else:
            assert requests in ("direct", "result_direct")
            if requests == "result_direct":
                conditions = tuple(
                    c for c in conditions if c.use.owner.definition.name == "result"
                )
                assert len(conditions) == 1
            selected_requests = tuple(
                ProjectSingleMatchRequest(owner=c.use.owner, use=c.use)
                for c in conditions
            )
        completed = with_project_single_match_requests(completed, selected_requests)
        assert completed.ok, completed.diagnostics
    bundle, owner = planning_inputs(completed)
    plan = plans.build_project_sql_plan(completed, bundle, owner, literal_policy=policy)
    assert isinstance(plan, plans.ProjectSQLPlan), "Probe requires a concrete plan."
    verified = verify_project_sql_plan(
        plan, completed, bundle, owner, literal_policy=policy
    )
    assert verified.verified
    return verified


def planning_inputs(completed):
    root = build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(root)
    assert checked.verified, "Probe requires verified original IR."
    bundle = build_project_query_block_ir_analysis_bundle(checked)
    owners = tuple(owner for owner in root.owners if owner.definition.name == "result")
    assert len(owners) == 1
    return bundle, owners[0]


def assessment(verified, mode="partial"):
    database = CapabilityProfileTarget(
        CapabilityProfileTargetKind.DATABASE, "postgresql", "18"
    )
    reference = CapabilityProfileReference(
        CapabilityProfileIdentity("phase65", "portable-probe"), "profile-1"
    )
    facts = ()
    if mode in ("applicable", "mismatch", "conflict", "residual"):
        (fact,) = tuple(f for f in _LOGICAL_TYPE_FACTS if f.key.subject == "Int")
        facts = (fact,)
        if mode == "conflict":
            facts += (replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED),)
    profile = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        reference,
        replace(database, release="17") if mode == "mismatch" else database,
        CapabilityProfileKind.BASE,
        (),
        tuple(
            CapabilityProfileFactOccurrence(reference, i, fact)
            for i, fact in enumerate(facts)
        ),
    )
    catalog = catalog_residual() if mode == "residual" else None
    request = (
        targets.prepare_project_sql_target_request()
        if mode == "omitted"
        else targets.prepare_project_sql_target_request(
            database, base=profile, catalog_context=catalog
        )
    )
    product = targets.build_project_sql_target_assessment(verified, request)
    checked = targets.verify_project_sql_target_assessment(product, verified, request)
    assert checked.verified
    return checked


def catalog_residual():
    from pietto._project.extension_catalog_availability import (
        DeclaredExtensionCatalogAvailability,
        select_extension_catalog,
    )
    from pietto._project.extension_signature_provider import (
        ExtensionSignatureProviderContext,
        ExtensionSignatureProviderSelectionOccurrence,
    )
    from pietto.semantic.capability_profiles import (
        CapabilityRequirementCollection,
        CapabilityRequirementCollectionIdentity,
        CapabilityRequirementOccurrence,
    )
    from pietto.semantic.extension_catalog import (
        ExtensionCatalogTarget,
        ExtensionCatalogLookupScope,
        ExtensionCatalogEntryFamily,
        PostgreSQLCallableIdentity,
    )
    from pietto.semantic.extension_signature_requirements import (
        ExtensionSignatureRequirementSelector,
        ExtensionSignatureRequirementSelectorOccurrence,
        ExtensionSignatureRequirementSelectors,
    )

    identity = CapabilityRequirementCollectionIdentity("phase65", "residual")
    key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="semantic missing",
        dialect="postgresql",
        extension="example_extension",
    )
    requirements = CapabilityRequirementCollection(
        identity, (CapabilityRequirementOccurrence(identity, 0, key),)
    )
    scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity("missing", ()),
    )
    selectors = ExtensionSignatureRequirementSelectors(
        requirements,
        (
            ExtensionSignatureRequirementSelectorOccurrence(
                0, ExtensionSignatureRequirementSelector(scope)
            ),
        ),
    )
    selection = select_extension_catalog(
        DeclaredExtensionCatalogAvailability(()),
        ExtensionCatalogTarget("PostgreSQL", "18", "example_extension", "1"),
    )
    return ExtensionSignatureProviderContext(
        selectors, (ExtensionSignatureProviderSelectionOccurrence(0, selection),)
    )


def _field(record, name):
    (field,) = tuple(f for f in record.fields if f.name == name)
    return field.value


def _record(product, original):
    (ref,) = tuple(ref for ref, value in product.bindings if value is original)
    (record,) = tuple(r for r in product.document.records if r.ref == ref)
    return record


def _change(document, record, name, value):
    (current,) = tuple(r for r in document.records if r.ref == record.ref)
    assert current.kind == record.kind and _field(current, name) != value
    changed = replace(
        current,
        fields=tuple(
            replace(f, value=value) if f.name == name else f for f in current.fields
        ),
    )
    return replace(
        document,
        records=tuple(changed if r is current else r for r in document.records),
    )


def _rejection(name, boundary, status, *, record=None, field=None):
    return {
        "name": name,
        "boundary": boundary,
        "status": status,
        "record_position": record,
        "field_position": field,
        "canonical_bytes": None,
    }


def runtime_summary(verified, product):
    view = inspect_project_sql_plan(verified)
    plan = view.plan
    report = reports.inspect_project_sql_requirement_report(product.context.report)
    source_map = maps.inspect_project_sql_source_map(product.context.source_map)
    assert len(report.entries) == len(plan.demands)
    for entry, demand in zip(report.entries, plan.demands, strict=True):
        assert entry.demand is demand and entry.ref is demand.ref
        assert source_map.origin(entry.origin.ref).original is entry.origin
    by_site = {}
    for association in source_map.source_map.associations:
        by_site.setdefault(id(association.site), []).append(association)
    for site in source_map.source_map.sites:
        assert source_map.reverse(site.source, site.occurrence) == tuple(
            by_site.get(id(site), ())
        )
    descriptors = []
    for source in plan.sources:
        callee = source.connector.callee
        assert isinstance(callee, DottedNameExpr)
        (argument,) = source.connector.arguments
        assert isinstance(argument, LiteralExpr) and type(argument.value) is str
        descriptors.append(
            [source.declaration.name, list(callee.parts), argument.value]
        )
    target = None
    if product.context.assessment is not None:
        assessed = targets.inspect_project_sql_target_assessment(
            product.context.assessment
        )
        summary = assessed.assessment.summary
        target = {
            "posture": summary.posture.value,
            "categories": [
                [key.value, len(values)] for key, values in summary.categories.items()
            ],
            "pending": len(summary.pending_realizations),
            "catalog_residuals": len(summary.catalog_residuals),
            "applicability": [
                lookup.profile_applicable for lookup in assessed.assessment.lookups
            ],
        }
    return {
        "definitions": [
            d.entry.owner.definition.name for d in plan.bindings.definitions
        ],
        "exports": [p.identity.name for p in plan.exports],
        "sources": descriptors,
        "policy": plan.literal_policy.value,
        "blocks": [b.kind.value for b in plan.blocks],
        "joins": [j.kind.value for j in plan.joins],
        "aggregations": [
            [a.mode.value, a.empty_input.value, len(a.keys)] for a in plan.aggregations
        ],
        "aggregates": [
            [
                len(a.arguments),
                a.value_type.resolved_type.name
                if a.value_type.resolved_type is not None
                else None,
                a.value_type.nullability.value,
            ]
            for a in plan.aggregates
        ],
        "windows": [[w.function.name, w.selected is not None] for w in plan.windows],
        "sets": [
            [s.kind.value, s.quantifier.value, len(s.operands), s.requires_equivalence]
            for s in plan.set_bodies
        ],
        "values": [
            [
                v.tag.value,
                v.value.hex()
                if type(v.value) is float
                else str(v.value)
                if type(v.value) is int
                else v.value,
            ]
            for v in plan.fixed_envelope.values
        ],
        "uses": len(plan.input_uses),
        "matches": [
            [
                m.request.scope.value,
                m.assessment.state.value,
                m.downstream_enforcement_required,
                len(m.joins),
            ]
            for m in plan.single_matches
        ],
        "proofs": [p.source.source.kind.value for p in plan.single_match_proofs],
        "hidden_order": len(plan.hidden_order_requirements),
        "risks": [r.kind.value for r in report.report.aggregate_evidence],
        "demand_families": [e.family.value for e in report.entries],
        "map_counts": [
            len(source_map.source_map.entries),
            len(source_map.source_map.sites),
            len(source_map.source_map.associations),
            len(source_map.source_map.links),
        ],
        "target": target,
    }


def mutations(name, verified, product):
    plan = verified.plan
    assert isinstance(plan, plans.ProjectSQLPlan)
    empty = schema.Value(schema.Tag.SEQUENCE, ())
    observations = []

    def reject(label, original, field, value):
        record = _record(product, original)
        changed = _change(product.document, record, field, value)
        outcome = pure.evaluate_project_sql_plan_document(changed)
        assert outcome.status is pure.Status.INVALID_RELATION, (
            name,
            label,
            outcome.status,
        )
        assert outcome.canonical_bytes is None
        observations.append(
            _rejection(
                label,
                "pure",
                outcome.status.value,
                record=outcome.record_position,
                field=outcome.field_position,
            )
        )

    if name == "minimal":
        reject("terminal_export_missing", plan, "result_exports", empty)
        (source,) = plan.sources
        (definition,) = tuple(
            d for d in plan.bindings.definitions if d.ref is source.ref
        )
        declarations = _field(_record(product, plan.bindings), "definitions").data
        assert isinstance(declarations, tuple) and len(declarations) == 2
        lost = schema.Value(schema.Tag.REF, _record(product, definition).ref)
        reject(
            "external_producer_missing",
            plan.bindings,
            "definitions",
            schema.Value(
                schema.Tag.SEQUENCE, tuple(v for v in declarations if v != lost)
            ),
        )
        (use,) = plan.input_uses
        (origin,) = tuple(
            o
            for o in plan.origins
            if o.subject is use.ref and o.role.value == "input_use"
        )
        mapped = maps.inspect_project_sql_source_map(product.context.source_map).origin(
            origin.ref
        )
        reject(
            "generated_marked_authored",
            mapped,
            "nature",
            schema.Value(schema.Tag.ENUM, "syntax_correspondence"),
        )
        (symbol,) = tuple(
            s
            for s in plan.symbols
            if s.namespace.value == "relation_use" and s.label == "rows"
        )
        changed = _change(
            product.document,
            _record(product, symbol),
            "label",
            schema.Value(schema.Tag.TEXT, "coherent_alternate_label"),
        )
        outcome = pure.evaluate_project_sql_plan_document(changed)
        assert outcome.status is pure.Status.OK and outcome.canonical_bytes is not None
        graft = copy(product)
        object.__setattr__(graft, "document", changed)
        object.__setattr__(graft, "canonical_bytes", outcome.canonical_bytes)
        assert not portable._corresponds(graft)
        checked = portable.verify_project_sql_plan_portable(graft, verified)
        assert checked.issues == (portable.RuntimeIssue.CORRESPONDENCE,)
        observations.append(
            {
                **_rejection(
                    "coherent_alternative", "correspondence", checked.issues[0].value
                ),
                "pure_status": "ok",
            }
        )
    if name == "imported_reexport":
        (symbol,) = tuple(
            s
            for s in plan.symbols
            if s.namespace.value == "relation_use" and s.label == "again"
        )
        (use,) = tuple(u for u in plan.input_uses if u.ref is symbol.subject)
        (foreign,) = tuple(
            d
            for d in plan.bindings.definitions
            if d.entry.owner.definition.name == "shared" and d.ref is not use.producer
        )
        reject(
            "same_looking_producer_graft",
            use,
            "producer",
            schema.Value(schema.Tag.REF, _record(product, foreign.ref).ref),
        )
    if name == "bound":
        (value,) = tuple(
            v
            for v in plan.fixed_envelope.values
            if type(v.value) is int
            and v.value == 1
            and v.slot.site.position.role is literals.ProjectSQLLiteralRole.LET
        )
        (demand,) = tuple(
            d
            for d in plan.demands
            if isinstance(d, literals.ProjectSQLLiteralDemand)
            and d.use.slot is value.slot
        )
        assert len(demand.contexts) == 2 and len(value.slot.site.position.ancestry) == 1
        reject("literal_contexts_missing", demand, "contexts", empty)
        reject(
            "literal_ancestry_shortened", value.slot.site.position, "ancestry", empty
        )
        (link,) = tuple(
            link
            for link in product.context.report.report.links
            if link.source.demand is demand and link.target.demand is demand.contexts[0]
        )
        reject(
            "literal_report_target_swapped",
            link,
            "target",
            schema.Value(schema.Tag.REF, _record(product, link.source).ref),
        )
        reject(
            "fixed_int_altered", value, "value", schema.Value(schema.Tag.INTEGER, "2")
        )
        reject(
            "fixed_int_as_bool", value, "value", schema.Value(schema.Tag.BOOLEAN, True)
        )
        reject(
            "fixed_int_as_float",
            value,
            "value",
            schema.Value(schema.Tag.FLOAT, (1.0).hex()),
        )
        stale = copy(verified)
        object.__setattr__(stale, "envelope", copy(verified.envelope))
        try:
            portable.build_project_sql_plan_portable(stale)
        except portable.TransportError as error:
            assert error.issue is portable.RuntimeIssue.INVALID_REQUEST
            observations.append(
                _rejection("stale_envelope", "runtime", error.issue.value)
            )
        else:
            raise AssertionError("A stale envelope was accepted")
    if name == "row_shared":
        supplied = product.context.assessment
        assert (
            supplied is not None
            and supplied.assessment.report is not product.context.report.report
        )
        (value,) = tuple(
            v
            for v in plan.fixed_envelope.values
            if type(v.value) is int
            and v.value == 1
            and v.slot.site.position.role is literals.ProjectSQLLiteralRole.LET
        )
        (demand,) = tuple(
            d
            for d in plan.demands
            if isinstance(d, literals.ProjectSQLLiteralDemand)
            and d.use.slot is value.slot
        )
        (link,) = tuple(
            link
            for link in product.context.report.report.links
            if link.source.demand is demand
        )
        (foreign,) = tuple(
            entry
            for entry in supplied.assessment.report.entries
            if entry.demand is demand.contexts[0]
        )
        reject(
            "cross_report_literal_target",
            link,
            "target",
            schema.Value(schema.Tag.REF, _record(product, foreign).ref),
        )
    if name == "join_right":
        (join,) = plan.joins
        assert join.kind.value == "right"
        reject(
            "join_nulling_rows_changed",
            join,
            "rows",
            schema.Value(schema.Tag.ENUM, "left_preserved"),
        )
    if name in ("join_semi", "join_anti"):
        (join,) = plan.joins
        (right,) = tuple(
            i for i in plan.join_inputs if i.join is join.ref and i.ordinal == 1
        )
        assert len(right.ports) == len(join.outputs) == 3
        reject("right_match_membership_missing", right, "ports", empty)
    if name == "global_empty":
        (aggregation,) = plan.aggregations
        assert aggregation.empty_input.value == "one_global_row"
        reject(
            "global_empty_row_lost",
            aggregation,
            "empty_input",
            schema.Value(schema.Tag.ENUM, "no_groups"),
        )
    if name == "hidden_distinct":
        (window,) = plan.windows
        assert window.selected is None
        (definition,) = tuple(
            d
            for d in plan.bindings.definitions
            if d.entry.owner is verified.selected_owner
        )
        (export,) = tuple(
            e for e in plan.result_exports if e.definition is definition.ref
        )
        reject(
            "hidden_window_export_leak",
            export,
            "port",
            schema.Value(schema.Tag.REF, _record(product, window.result).ref),
        )
        reject("qualify_window_missing", plan, "windows", empty)
    if name == "group_hidden":
        (definition,) = tuple(
            d
            for d in plan.bindings.definitions
            if d.entry.owner is verified.selected_owner
        )
        (export,) = tuple(
            e for e in plan.result_exports if e.definition is definition.ref
        )
        (key,) = tuple(k for k in plan.group_keys if k.position == 0)
        reject(
            "hidden_group_export_leak",
            export,
            "port",
            schema.Value(schema.Tag.REF, _record(product, key.result).ref),
        )
    if name == "aggregate_risks":
        assert plan.aggregate_risks
        reject("retained_aggregate_risks_missing", plan, "aggregate_risks", empty)
    if name == "shared_set":
        (body,) = tuple(s for s in plan.set_bodies if s.kind.value == "except")
        (column,) = tuple(c for c in plan.set_columns if c.body is body.ref)
        assert len(column.inputs) == 2 and column.value_inputs == column.inputs[:1]
        record = _record(product, column)
        inputs = _field(record, "inputs").data
        assert isinstance(inputs, tuple)
        reject(
            "except_right_membership_missing",
            column,
            "inputs",
            schema.Value(schema.Tag.SEQUENCE, inputs[:1]),
        )
        (item,) = plan.order_items
        determination = _field(_record(product, item), "determination").data
        assert isinstance(determination, tuple) and len(determination) == 3
        reject(
            "visible_order_proof_missing",
            item,
            "determination",
            schema.Value(
                schema.Tag.SEQUENCE, (determination[0], empty, determination[2])
            ),
        )
    if name == "set_forms":
        (definition,) = tuple(
            d
            for d in plan.bindings.definitions
            if d.entry.owner is verified.selected_owner
        )
        (body,) = tuple(b for b in plan.set_bodies if b.definition is definition.ref)
        (operand,) = tuple(
            o for o in plan.set_operands if o.body is body.ref and o.position == 0
        )
        (input_,) = tuple(i for i in plan.set_inputs if i.operand is operand.ref)
        assert input_.evidence.parents
        reject("decimal_parent_missing", input_.evidence, "parents", empty)
        operands = _field(_record(product, body), "operands").data
        assert isinstance(operands, tuple) and len(operands) == 2
        reject(
            "set_operands_swapped",
            body,
            "operands",
            schema.Value(schema.Tag.SEQUENCE, tuple(reversed(operands))),
        )
    if name == "hidden_order":
        (hidden,) = plan.hidden_order_requirements
        assert hidden.proof.closure.witness
        reject("hidden_order_proof_missing", hidden.proof.closure, "witness", empty)
    if name in ("proof_right_limit", "proof_right_global"):
        (proof,) = plan.single_match_proofs
        assert proof.source.premise_nodes
        reject("producer_proof_premise_missing", proof.source, "premise_nodes", empty)
    if name == "path_complete":
        (proof,) = tuple(
            p
            for p in plan.single_match_proofs
            if p.source.source.kind.value == "whole_path"
        )
        assert len(proof.children) == 2
        reject("whole_path_child_missing", proof, "children", empty)
    if name == "sharing_depth12":
        (definition,) = tuple(
            d
            for d in plan.bindings.definitions
            if d.entry.owner.definition.name == "p12"
        )
        (body,) = tuple(b for b in plan.set_bodies if b.definition is definition.ref)
        (operand,) = tuple(
            o for o in plan.set_operands if o.body is body.ref and o.position == 1
        )
        record = _record(product, plan)
        uses = _field(record, "input_uses").data
        assert isinstance(uses, tuple) and len(uses) == 26
        lost = schema.Value(schema.Tag.REF, _record(product, operand.use).ref)
        assert uses.count(lost) == 1
        reject(
            "repeated_use_missing",
            plan,
            "input_uses",
            schema.Value(schema.Tag.SEQUENCE, tuple(v for v in uses if v != lost)),
        )
    if name == "window_value_named":
        (window,) = tuple(w for w in plan.windows if w.function.name == "first_value")
        assert window.authored is not window.effective
        (association,) = tuple(
            a
            for a in product.context.source_map.source_map.associations
            if a.kind.value == "effective_to_authored_window"
            and a.observed is window.effective
            and a.entry.original.subject is window.ref
        )
        reject(
            "effective_window_marked_authored",
            association,
            "kind",
            schema.Value(schema.Tag.ENUM, "authored_cause"),
        )
    if name == "limit_before_filter":
        from pietto._project.project_ir_properties import (
            ProjectIRPropertyStage,
            ProjectIRProvidedRelationOrdering,
        )

        (boundary,) = tuple(
            b for b in plan.result_boundaries if b.kind.value == "relation_ordering"
        )
        assert isinstance(boundary.properties, ProjectIRPropertyStage)
        (provided,) = tuple(
            p
            for p in boundary.properties.provided
            if type(p) is ProjectIRProvidedRelationOrdering
            and p.output.occurrence.producer is boundary.operator.node
        )
        reject("provided_order_items_missing", provided, "items", empty)
    if name.startswith("target_"):
        supplied = product.context.assessment
        assert supplied is not None
        target = supplied.assessment
        reject(
            "false_target_completion",
            target.summary,
            "posture",
            schema.Value(schema.Tag.ENUM, "complete_requirements_satisfied"),
        )
        if name == "target_applicable":
            assert target.summary.pending_realizations
            reject(
                "target_residuals_missing",
                target.summary,
                "pending_realizations",
                empty,
            )
        if name == "target_mismatch":
            (lookup,) = tuple(
                q
                for q in target.lookups
                if q.kind.value == "compiler_type_identity" and q.key.subject == "Int"
            )
            assert not lookup.profile_applicable
            reject(
                "false_profile_applicability",
                lookup,
                "profile_applicable",
                schema.Value(schema.Tag.BOOLEAN, True),
            )
        if name == "target_residual":
            assert len(target.request.catalog_residuals) == 1
            reject(
                "catalog_residual_missing", target.request, "catalog_residuals", empty
            )
        if name == "target_conflict":
            (lookup,) = tuple(
                q
                for q in target.lookups
                if q.kind.value == "compiler_type_identity" and q.key.subject == "Int"
            )
            record = _record(product, lookup.profile_result)
            assert record.kind == "conflict"
            evidence = _field(record, "evidence").data
            assert isinstance(evidence, tuple) and len(evidence) == 2
            reject(
                "conflicting_fact_missing",
                lookup.profile_result,
                "evidence",
                schema.Value(schema.Tag.SEQUENCE, evidence[:1]),
            )
    return observations


_NEGATIVE_SET = SET_FLOAT.replace("Float", "Int").replace(
    "query result:", "table combined:"
)
NEGATIVE_CORPUS = (
    (
        "connector",
        CONTROL.replace('postgres.table("rows")', "postgres.table(1)"),
        "PIE-S2306",
    ),
    (
        "unrelated_error",
        CONTROL + "source broken: Row is postgres.table(1)\n",
        "PIE-S2306",
    ),
    (
        "general_call",
        CONTROL.replace("        id\n", '        value = trim("hello")\n'),
        "call_authority_unavailable",
    ),
    (
        "order_evidence",
        CONTROL.replace("        id\n", "        renamed = id\n")
        + "    order by:\n        renamed\n",
        "order",
    ),
    (
        "float_distinct",
        CONTROL.replace("id: Int", "id: Float").replace(
            "    select:", "    select distinct:"
        ),
        "PIE-S2339",
    ),
    ("float_set", SET_FLOAT.replace("union all", "union distinct"), "PIE-S2344"),
    (
        "set_group",
        _NEGATIVE_SET
        + "query result:\n    from combined\n    group by:\n        id\n    select:\n        total = count()\n",
        "PIE-S2333",
    ),
    (
        "set_global",
        _NEGATIVE_SET
        + "query result:\n    from combined\n    select:\n        total = count()\n",
        "PIE-S2333",
    ),
    (
        "global_satisfying",
        ORDINARY_PREFIX
        + "query result:\n    from rows\n    select:\n        total = count()\n    satisfying:\n        total > 0\n",
        "PIE-S2333",
    ),
    ("qualify_without_window", CONTROL + "    qualify:\n        id > 0\n", "PIE-S2331"),
    (
        "global_window",
        ORDINARY_PREFIX
        + "query result:\n    from rows\n    select:\n        total = count()\n        w = row_number() window:\n            order by:\n                total\n",
        "PIE-S2333",
    ),
)


def source_negative(workspace, source, expected):
    completed = _completed(workspace, source)
    bundle, owner = planning_inputs(completed)
    value = plans.build_project_sql_plan(completed, bundle, owner)
    assert isinstance(value, plans.ProjectSQLPlanUnavailable)
    diagnostics = [[d.code, d.severity.value] for d in completed.diagnostics]
    blockers = [b.kind.value for b in value.blockers]
    if expected.startswith("PIE-"):
        assert not completed.ok and [expected, "error"] in diagnostics
        boundary, status = "semantic", "error"
    else:
        assert completed.ok and expected in blockers
        boundary, status = "planning", "unavailable"
    return {
        "boundary": boundary,
        "status": status,
        "diagnostics": diagnostics,
        "blockers": blockers,
        "canonical_bytes": None,
    }


def raw_rejections():
    cases = (
        ("duplicate_key", b'{"format":"x","format":"x"}', pure.Status.DUPLICATE_KEY),
        ("invalid_utf8", b"\xff", pure.Status.INVALID_UTF8),
        ("nonfinite_number", b'{"x":NaN}', pure.Status.INVALID_VALUE),
        ("negative_zero_ref", b'{"x":-0}', pure.Status.INVALID_VALUE),
        (
            "unknown_format",
            b'{"format":"future","records":[]}',
            pure.Status.UNKNOWN_FORMAT,
        ),
        (
            "unknown_record",
            (
                '{"format":"'
                + schema.FORMAT
                + '","records":[{"kind":"future","ref":["future",0],"fields":[]}]}'
            ).encode(),
            pure.Status.INVALID_RECORD,
        ),
        (
            "unknown_envelope_field",
            ('{"format":"' + schema.FORMAT + '","records":[],"future":1}').encode(),
            pure.Status.INVALID_DOCUMENT,
        ),
        (
            "unknown_record_field",
            (
                '{"format":"'
                + schema.FORMAT
                + '","records":[{"kind":"observation","ref":["observation",0],"fields":[["future",["absent",null]]]}]}'
            ).encode(),
            pure.Status.INVALID_FIELD,
        ),
        (
            "wrong_ref_domain_coordinates",
            (
                '{"format":"'
                + schema.FORMAT
                + '","records":[{"kind":"observation","ref":["observation",0],"fields":[["plan",["ref",["source_def",0]]],["report",["absent",null]],["source_map",["absent",null]],["assessment",["absent",null]]]}]}'
            ).encode(),
            pure.Status.INVALID_REF,
        ),
        (
            "input_bytes_limit",
            b" " * (schema.MAX_BYTES + 1),
            pure.Status.RESOURCE_LIMIT,
        ),
        (
            "input_depth_limit",
            b"[" * (schema.MAX_DEPTH + 1) + b"]" * (schema.MAX_DEPTH + 1),
            pure.Status.RESOURCE_LIMIT,
        ),
    )
    observed = []
    for name, raw, expected in cases:
        outcome = pure.parse_project_sql_plan_document(raw)
        assert outcome.status is expected, (name, outcome.status)
        assert outcome.canonical_bytes is None
        observed.append(
            _rejection(
                name,
                "raw",
                outcome.status.value,
                record=outcome.record_position,
                field=outcome.field_position,
            )
        )
    return observed


def observation(workspace: Path) -> dict[str, object]:
    cases = []
    for name, source, policy in CORPUS:
        observations = []
        first_product = None
        for iteration in (0, 1):
            verified = construction(
                workspace / name / str(iteration),
                source,
                policy,
                requests=REQUEST_MODES.get(name),
            )
            supplied = (
                assessment(verified)
                if name in ("bound", "row_shared")
                else assessment(verified, name.removeprefix("target_"))
                if name.startswith("target_")
                else None
            )
            report = (
                reports.verify_project_sql_requirement_report(
                    reports.build_project_sql_requirement_report(verified), verified
                )
                if name == "row_shared"
                else None
            )
            product = portable.build_project_sql_plan_portable(
                verified, report=report, assessment=supplied
            )
            assert portable.verify_project_sql_plan_portable(
                product, verified, assessment=supplied
            ).verified
            decoded = pure.parse_project_sql_plan_document(product.canonical_bytes)
            assert decoded.status is pure.Status.OK
            assert decoded.canonical_bytes == product.canonical_bytes
            assert decoded.document == product.document
            missing = replace(product.document, records=())
            rejected = pure.evaluate_project_sql_plan_document(missing)
            assert (
                rejected.status is not pure.Status.OK
                and rejected.canonical_bytes is None
            )
            if first_product is not None:
                foreign = portable.verify_project_sql_plan_portable(
                    first_product, verified, assessment=supplied
                )
                assert foreign.issues == (portable.RuntimeIssue.INVALID_REQUEST,)
            else:
                first_product = product
            observations.append(
                {
                    "document": product.canonical_bytes.decode("utf-8"),
                    "rejection": rejected.status.value,
                    "summary": runtime_summary(verified, product),
                    "mutations": mutations(name, verified, product),
                    "cross_snapshot": "invalid_runtime_request",
                }
            )
        assert observations[0] == observations[1]
        cases.append({"case": name, **observations[0]})
    duplicate = pure.parse_project_sql_plan_document(b'{"format":"x","format":"x"}')
    assert duplicate.status is pure.Status.DUPLICATE_KEY
    negatives = []
    for name, source, expected in NEGATIVE_CORPUS:
        first = source_negative(workspace / "negative" / name / "0", source, expected)
        second = source_negative(workspace / "negative" / name / "1", source, expected)
        assert first == second
        negatives.append({"case": name, **first})
    return {
        "format": "pietto.phase65-sql-plan-differential.v1",
        "cases": cases,
        "duplicate_key": duplicate.status.value,
        "source_negatives": negatives,
        "raw_rejections": raw_rejections(),
    }


def render(value: object, workspace: Path) -> bytes:
    assert isinstance(workspace, Path)
    return (
        json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        output = render(observation(arguments.workspace), arguments.workspace)
    except Exception:
        sys.stderr.write("Phase65 portable probe failed.\n")
        return 1
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
