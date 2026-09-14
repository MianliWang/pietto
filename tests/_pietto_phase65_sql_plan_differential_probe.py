"""Small real-source Phase65 observations through the existing process matrix."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

from _pietto_phase64_flat_ir_differential_probe import _completed, CONTROL, FD_SOURCE
from pietto._project import project_sql_plan as plans
from pietto._project import project_sql_plan_literals as literals
from pietto._project import project_sql_plan_portable as portable
from pietto._project import project_sql_plan_pure_boundary as pure
from pietto._project import project_sql_plan_target_assessment as targets
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
)

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
CORPUS = (
    ("minimal", CONTROL, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
    ("bound", BOUND_SOURCE, literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS),
    ("shared_set", SET_SOURCE, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
    ("staged", STAGED_SOURCE, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
    ("hidden_order", FD_SOURCE, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS),
)


def construction(workspace: Path, source: str, policy):
    completed = _completed(workspace, source)
    root = build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(root)
    assert checked.verified, "Probe requires verified original IR."
    bundle = build_project_query_block_ir_analysis_bundle(checked)
    owners = tuple(owner for owner in root.owners if owner.definition.name == "result")
    assert len(owners) == 1
    plan = plans.build_project_sql_plan(
        completed, bundle, owners[0], literal_policy=policy
    )
    assert isinstance(plan, plans.ProjectSQLPlan), "Probe requires a concrete plan."
    verified = verify_project_sql_plan(
        plan, completed, bundle, owners[0], literal_policy=policy
    )
    assert verified.verified
    return verified


def assessment(verified):
    database = CapabilityProfileTarget(
        CapabilityProfileTargetKind.DATABASE, "postgresql", "18"
    )
    profile = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        CapabilityProfileReference(
            CapabilityProfileIdentity("phase65", "portable-probe"), "profile-1"
        ),
        database,
        CapabilityProfileKind.BASE,
        (),
        (),
    )
    request = targets.prepare_project_sql_target_request(database, base=profile)
    product = targets.build_project_sql_target_assessment(verified, request)
    checked = targets.verify_project_sql_target_assessment(product, verified, request)
    assert checked.verified
    return checked


def observation(workspace: Path) -> dict[str, object]:
    cases = []
    for name, source, policy in CORPUS:
        observations = []
        for iteration in (0, 1):
            verified = construction(workspace / name / str(iteration), source, policy)
            supplied = assessment(verified) if name == "bound" else None
            product = portable.build_project_sql_plan_portable(
                verified, assessment=supplied
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
            observations.append(
                {
                    "document": product.canonical_bytes.decode("utf-8"),
                    "rejection": rejected.status.value,
                }
            )
        assert observations[0] == observations[1]
        cases.append({"case": name, **observations[0]})
    duplicate = pure.parse_project_sql_plan_document(b'{"format":"x","format":"x"}')
    assert duplicate.status is pure.Status.DUPLICATE_KEY
    return {
        "format": "pietto.phase65-sql-plan-differential.v1",
        "cases": cases,
        "duplicate_key": duplicate.status.value,
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
