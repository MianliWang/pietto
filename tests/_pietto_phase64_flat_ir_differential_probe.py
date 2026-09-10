"""Real flat-algebra records, bytes and rejections through existing process cells."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import argparse
import json
import sys

from _pietto_phase63_query_block_ir_differential_probe import _portable_records, render
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
    with_project_single_match_requests,
)
from pietto._project.project_single_match import ProjectSingleMatchRequest
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRCompletedSetOperationOutput,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_query_block_ir_inspection import (
    build_project_query_block_ir_inspection,
)
from pietto._project import project_query_block_ir_pure_boundary as pure

SEED_ENVIRONMENT = "PIETTO_PHASE64_SLICE10_AMBIENT"
SOURCE = """shape Row:
    id: Decimal(10, 2) nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
table dedup:
    from lhs
    select distinct:
        id
    order by:
        id
    limit 2
table combined:
    union all:
        from dedup
        from rhs
        from dedup
table limited:
    from rhs
    select:
        id
    limit 1
table joined:
    from combined
    semi join limited as r:
        from combined
        on true
    select distinct:
        id = combined.id
table final:
    except distinct:
        from joined
        from joined
        from joined
query result:
    from final
    select:
        id
"""
CONTROL = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        id
"""


FD_SOURCE = """shape Row:
    value: Int not null
    hidden: Float nullable
    unique by_value on value
source rows: Row is postgres.table("rows")
query result:
    from rows
    select distinct:
        value
    order by:
        hidden
"""


def _completed(
    root: Path, source: str, *, imported_alias: bool = False
) -> ProjectConcreteCompletedSemanticResult:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    if imported_alias:
        (root / "types.pietto").write_text(
            "type Base = Decimal(10, 2)\nexport:\n    type Base\n"
        )
        (root / "facade.pietto").write_text(
            'import "types.pietto":\n    type Base as Public\nexport:\n    type Public\n'
        )
    (root / "main.pietto").write_text(source)
    parsed = check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    return completed


def observation(workspace: Path) -> dict[str, object]:
    observations = []
    for label, source in (
        ("proved", SOURCE),
        ("unproved", SOURCE.replace("limit 1", "limit 2")),
        (
            "alias",
            'import "facade.pietto":\n    type Public as Alias\n'
            + SOURCE.replace("id: Decimal(10, 2) nullable", "id: Alias nullable"),
        ),
        ("strict_fd", FD_SOURCE),
        ("v1_control", CONTROL),
    ):
        completed = _completed(
            workspace / label, source, imported_alias=label == "alias"
        )
        if label in {"proved", "unproved", "alias"}:
            condition = completed.roots.join_conditions.entries[0]
            request = ProjectSingleMatchRequest(
                owner=condition.use.owner, use=condition.use
            )
            completed = with_project_single_match_requests(
                completed, (request, request)
            )
        root = build_project_query_block_ir(completed)
        verified = verify_project_query_block_ir(root)
        assert verified.verified, verified.issues
        product = build_project_query_block_ir_inspection(
            build_project_query_block_ir_analysis_bundle(verified)
        )
        if label == "v1_control":
            assert (
                product.document.format_marker
                == pure.PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT
            )
        elif label == "strict_fd":
            assert not root.requirements
            assert any(
                record.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF
                and next(
                    field.value.enumeration
                    for field in record.fields
                    if field.key == "mode"
                )
                == "strict_fd"
                for record in product.document.records
            )
        else:
            assert (
                product.document.format_marker
                == pure.PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
            )
            assert len(root.requirements) == 2
            assert [item.assessment.state.value for item in root.requirements] == [
                "legal_unproved" if label == "unproved" else "proved"
            ] * 2
            sets = tuple(
                e
                for e in root.entries
                if isinstance(e, ProjectIRCompletedSetOperationOutput)
            )
            assert len(sets) == 2
            for entry in sets:
                assert len(entry.operands) == 3
                assert entry.operands[0].producer is entry.operands[2].producer
                assert entry.uses[0] is not entry.uses[2]
                assert all(
                    use.use.output is use.producer.active_output.occurrence
                    for use in entry.operands
                )
            joined = next(
                e for e in root.entries if e.owner.definition.name == "joined"
            )
            assert isinstance(joined, ProjectIRCompletedQueryBlockOutput)
            assert joined.join_prefix is not None
            assert (
                joined.join_prefix.final_join.condition
                is completed.roots.join_conditions.entries[0]
            )
        negatives = []
        kinds = (
            (pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY,)
            if label == "v1_control"
            else (pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF,)
            if label == "strict_fd"
            else (
                pure.ProjectQueryBlockIRRecordKind.CONDITION,
                pure.ProjectQueryBlockIRRecordKind.SET_OPERAND,
                pure.ProjectQueryBlockIRRecordKind.DISTINCT,
                pure.ProjectQueryBlockIRRecordKind.REQUIREMENT,
            )
        )
        for kind in kinds:
            malformed = replace(
                product.document,
                records=tuple(
                    record
                    for record in product.document.records
                    if record.kind is not kind
                ),
            )
            rejected = pure.evaluate_project_query_block_ir_document(malformed)
            assert rejected.status is not pure.ProjectQueryBlockIRPureStatus.OK
            assert rejected.canonical_bytes is None
            negatives.append(
                [
                    kind.value,
                    rejected.status.value,
                    rejected.record_position,
                    rejected.field_position,
                ]
            )
        if label != "v1_control":
            declared = {
                field.value.ref: record
                for record in product.document.records
                for field in record.fields
                if field.key == "ref"
            }
            for record in product.document.records:
                values = {field.key: field.value for field in record.fields}
                if record.kind is pure.ProjectQueryBlockIRRecordKind.ORDER_PROOF:
                    binding = {
                        field.key: field.value
                        for field in declared[values["binding"].ref].fields
                    }
                    assert (
                        values["visible"] == binding["visible"]
                        and values["targets"] == binding["targets"]
                    )
                    if values["mode"].enumeration == "strict_fd":
                        assert (
                            values["seed"].refs
                            and values["requested"].refs
                            and values["steps"].texts
                        )
                elif (
                    record.kind
                    is pure.ProjectQueryBlockIRRecordKind.TYPE_PARAMETER_SOURCE
                ):
                    assert values["parameters"].integers == (10, 2)
                    site = values["site"].text
                    assert site is not None
                    assert json.loads(site)["path"] == (
                        "types.pietto" if label == "alias" else "main.pietto"
                    )
        observations.append(
            {
                "case": label,
                "records": _portable_records(product.document),
                "bytes": product.canonical_bytes.decode("utf-8"),
                "rejections": negatives,
            }
        )
    return {"format": "pietto.phase64-flat-ir-differential.v1", "cases": observations}


__all__ = ("observation", "render")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args()
    sys.stdout.buffer.write(
        render(observation(arguments.workspace), arguments.workspace)
    )


if __name__ == "__main__":
    main()
