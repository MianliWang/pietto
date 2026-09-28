"""Offline audit support, not a proof of completion or external execution."""

from dataclasses import asdict
import importlib
import importlib.util
from pathlib import Path
import re
import sys

import _pietto_phase67_arrow_compatibility_probe as sdk
import _pietto_phase67_result_product_probe as product

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/phases/phase-67/completion-audit.md"
ENTRY = AUDIT.with_name("slice-16.md")


def test_audit_references_resolve_to_actual_owner_and_consumer_files():
    document = AUDIT.read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)]+\.py)\)", document)
    assert targets
    for target in targets:
        path = (AUDIT.parent / target).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), target
    owners = {
        "project_result_contract": ("build_result_contract", "verify_result_contract"),
        "project_result_binding": ("bind_producer", "verify_producer_binding"),
        "project_arrow_result": ("bind_arrow", "verify_batch"),
        "project_result_contract_correspondence": (
            "verify_contract_correspondence",
            "verify_bound_export",
        ),
        "project_scalar_meaning": ("acquire_scalar_meaning", "verify_scalar_meaning"),
        "project_result_reader": ("open_finite_reader", "verify_finite_completion"),
        "project_result_ingress": ("ingest_rows", "ingest_batch", "ingest_reader"),
        "project_result_ipc": ("encode_ipc", "open_ipc", "verify_ipc_completion"),
    }
    for name, entries in owners.items():
        module = importlib.import_module("pietto._project." + name)
        assert getattr(module, "__all__") == ()
        for entry in entries:
            assert callable(getattr(module, entry)) and entry in document
    assert importlib.util.find_spec("pyarrow") is None
    assert "pyarrow" not in sys.modules


def test_audit_keeps_batch_stream_codec_and_frame_limits_distinct():
    from pietto._project.project_arrow_result import BatchLimits
    from pietto._project.project_result_reader import FiniteReaderLimits
    from pietto._project.project_result_contract_pure_boundary import DocumentLimits
    from pietto._project.project_result_ipc import IPCLimits

    batch, finite, document = BatchLimits(), FiniteReaderLimits(), DocumentLimits()
    assert asdict(batch) == dict(fields=64, rows=4096, bytes=8 * 1024 * 1024)
    assert (finite.max_batches, finite.max_total_rows, finite.max_total_bytes) == (
        1024,
        1048576,
        64 * 1024 * 1024,
    )
    assert asdict(document) == dict(
        bytes=4 * 1024 * 1024,
        depth=48,
        values=65536,
        records=8192,
        references=16384,
        text=131072,
        total_text=2 * 1024 * 1024,
        fields=1024,
    )
    assert IPCLimits().max_bytes == 96 * 1024 * 1024
    text = AUDIT.read_text(encoding="utf-8")
    for fact in ("1024 fields", "16384 references", "131072bytes", "header100bytes"):
        assert fact in text


def test_existing_required_consumers_remain_the_behavioral_denominator():
    assert len(product.CASES) == len(set(product.CASES)) == 120
    assert len(sdk.CASES) == 9
    whole, real = product._whole(), product._integration()
    assert product.CASES[-10:] == whole.GROUPS
    assert len(real.CELLS) == 8 and len(real.RECIPES) == 4
    assert len(real.product_damage()) == 8 and len(whole.damage()) == 10
    document = AUDIT.read_text(encoding="utf-8")
    assert all(group in document for group in whole.GROUPS)
    assert "不是S16运行证据" in document
    assert "不生成完成证明" in document


def test_candidate_has_one_conditional_closure_and_an_external_record():
    entry = ENTRY.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    assert entry.count("## 唯一闭环规则") == 1
    assert "slice-16.md#唯一闭环规则" in audit
    for fact in (
        "ACTIVE / CANDIDATE",
        "completion candidate pending S16 closure",
        "Phase68 **NOT STARTED**",
        "pietto-phase67-slice16-final-state.json",
        "当前文档不预言它们",
        "status-only follow-up commit",
    ):
        assert fact in entry
    assert "当前S16不是已完成发布" in entry


def test_outgoing_handoff_preserves_evidence_layers_and_later_owners():
    document = AUDIT.read_text(encoding="utf-8")
    for boundary in (
        "descriptor-only",
        "五类captured-native",
        "原mapping",
        "PyArrow-backed CPU",
        "unknown cardinality",
        "不得hidden COUNT",
        "Phase68独立FULL phase-initiation",
        "不启动Slice1",
        "INSUFFICIENT_EVIDENCE",
        "comparable_samples=0",
        "protocol_nullable=None",
        "checked reader本身不升级ownership",
    ):
        assert boundary in document
    for phase in (69, 71, 80, 82, 83, 84, 86, 90):
        assert f"Phase{phase}" in document
    assert "Phase91–97仅tentative/owner-only" in document


def test_promoted_lessons_link_to_preserved_contracts_and_consumers():
    path = ROOT / "docs/references/engineering-lessons.md"
    section = path.read_text(encoding="utf-8").split(
        "## Phase67 完成审计的六条耐久教训", 1
    )[1]
    targets = re.findall(r"\]\(([^)]+)\)", section)
    assert targets
    for target in targets:
        resolved = (path.parent / target.split("#", 1)[0]).resolve()
        assert resolved.is_relative_to(ROOT) and resolved.is_file(), target
