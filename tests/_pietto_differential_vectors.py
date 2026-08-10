"""Frozen private differential-vector corpus for the Rust-ready pure boundary.

The corpus is an internal test asset. It is not a public fixture, a package
manifest, a cache format, or a compatibility promise to any external consumer.

Every vector carries a complete portable input plus its stored expected result.
Expected payloads live in one clearly marked literal block below; they are
reviewed authority, never derived from the implementation under test at run
time. ``_pietto_differential_harness.propose_expected_updates`` is the only
authoring path, and it proposes a diff rather than rewriting this file.

No vector depends on an absolute path, a temporary directory, a memory address,
an object identifier, host metadata, a timestamp, or version-control state.
"""

from __future__ import annotations

from _pietto_differential_harness import (
    DIFFERENTIAL_VECTOR_FORMAT,
    DifferentialClassification,
    DifferentialPurpose,
    DifferentialVector,
)
from collections.abc import Mapping
from types import MappingProxyType

from pietto._project.module_pure_boundary import (
    PURE_ABSENT,
    PURE_DOCUMENT_FORMAT_MARKER,
    PURE_MAX_INTEGER,
    ProjectPureDocument,
    ProjectPureField,
    ProjectPureRecord,
    ProjectPureStatus,
    ProjectPureTag,
    ProjectPureValue,
    pure_boolean,
    pure_enumeration,
    pure_integer,
    pure_text,
)

_EVALUATION = DifferentialClassification.PORTABLE_EVALUATION
_REJECTION = DifferentialClassification.PORTABLE_REJECTION

_DIGEST_A = "1" * 64
_DIGEST_B = "2" * 64


def _record(
    kind: str,
    *pairs: tuple[str, ProjectPureValue],
) -> ProjectPureRecord:
    """Build one portable record from ordered key and value pairs."""

    return ProjectPureRecord(
        kind=kind,
        fields=tuple(ProjectPureField(key=key, value=value) for key, value in pairs),
    )


def _document(*records: ProjectPureRecord) -> ProjectPureDocument:
    """Build one portable document from ordered records."""

    return ProjectPureDocument(records=records)


def _header(
    modules: int, marker: str = PURE_DOCUMENT_FORMAT_MARKER
) -> ProjectPureRecord:
    """Build the mandatory ``inspection`` header record."""

    return _record(
        "inspection",
        ("format", pure_enumeration(marker)),
        ("modules", pure_integer(modules)),
    )


_OWNER = _record(
    "owner",
    ("kind", pure_enumeration("local_project_root")),
    ("namespace", pure_text("")),
    ("name", pure_text("")),
)


def _module(index: int, path: str) -> ProjectPureRecord:
    """Build one ``module`` record."""

    return _record("module", ("module", pure_integer(index)), ("path", pure_text(path)))


def _digest(
    index: int, digest: str = _DIGEST_A, byte_count: int = 12
) -> ProjectPureRecord:
    """Build one ``digest`` record."""

    return _record(
        "digest",
        ("module", pure_integer(index)),
        ("algorithm", pure_enumeration("sha256_opened_bytes")),
        ("digest", pure_text(digest)),
        ("byte_count", pure_integer(byte_count)),
    )


def _readiness(
    index: int,
    *,
    status: str = "ready",
    reason: str = "trusted_local_source_resolved",
    cycles: int = 0,
) -> ProjectPureRecord:
    """Build one ``readiness`` record."""

    return _record(
        "readiness",
        ("module", pure_integer(index)),
        ("status", pure_enumeration(status)),
        ("reason", pure_enumeration(reason)),
        ("cycles", pure_integer(cycles)),
    )


def _cycle(index: int, cycle: int, members: int) -> ProjectPureRecord:
    """Build one ``readiness_cycle`` record."""

    return _record(
        "readiness_cycle",
        ("module", pure_integer(index)),
        ("cycle", pure_integer(cycle)),
        ("members", pure_integer(members)),
    )


def _cycle_member(index: int, cycle: int, member: int, path: str) -> ProjectPureRecord:
    """Build one ``readiness_cycle_member`` record."""

    return _record(
        "readiness_cycle_member",
        ("module", pure_integer(index)),
        ("cycle", pure_integer(cycle)),
        ("member", pure_integer(member)),
        ("path", pure_text(path)),
    )


def _graph(
    index: int,
    *,
    cyclic: bool = False,
    members: int = 1,
    targets: int = 0,
    evidence: int = 0,
) -> ProjectPureRecord:
    """Build one ``graph`` record."""

    return _record(
        "graph",
        ("module", pure_integer(index)),
        ("component_is_cyclic", pure_boolean(cyclic)),
        ("component_members", pure_integer(members)),
        ("dependency_targets", pure_integer(targets)),
        ("import_evidence", pure_integer(evidence)),
    )


def _component_member(index: int, member: int, path: str) -> ProjectPureRecord:
    """Build one ``graph_component_member`` record."""

    return _record(
        "graph_component_member",
        ("module", pure_integer(index)),
        ("member", pure_integer(member)),
        ("path", pure_text(path)),
    )


def _dependency_target(index: int, target: int, path: str) -> ProjectPureRecord:
    """Build one ``graph_dependency_target`` record."""

    return _record(
        "graph_dependency_target",
        ("module", pure_integer(index)),
        ("target", pure_integer(target)),
        ("path", pure_text(path)),
    )


def _import_evidence(
    index: int,
    evidence: int,
    path: str,
    statement: int = 0,
    item: int = 0,
) -> ProjectPureRecord:
    """Build one ``graph_import_evidence`` record."""

    return _record(
        "graph_import_evidence",
        ("module", pure_integer(index)),
        ("evidence", pure_integer(evidence)),
        ("path", pure_text(path)),
        ("module_statement_position", pure_integer(statement)),
        ("item_position", pure_integer(item)),
    )


def _module_block(
    index: int,
    path: str,
    *,
    digest: str = _DIGEST_A,
    cyclic: bool = False,
) -> tuple[ProjectPureRecord, ...]:
    """Build one minimal complete module scope in exact section order."""

    return (
        _module(index, path),
        _digest(index, digest),
        _readiness(index),
        _graph(index, cyclic=cyclic),
        _component_member(index, 0, path),
    )


def _import(
    index: int,
    request: int,
    *,
    local_name: str,
    exported_name: str,
    target_module_path: str,
    namespace: str = "type",
    declaration_kind: str = "shape",
    statement: int = 0,
    item: int = 0,
    resolved: bool = True,
    issues: int = 0,
) -> ProjectPureRecord:
    """Build one ``import`` record with or without a resolved nominal target."""

    return _record(
        "import",
        ("module", pure_integer(index)),
        ("request", pure_integer(request)),
        ("local_name", pure_text(local_name)),
        ("namespace", pure_enumeration(namespace)),
        ("declaration_kind", pure_enumeration(declaration_kind)),
        ("target_module_path", pure_text(target_module_path)),
        ("exported_name", pure_text(exported_name)),
        ("module_statement_position", pure_integer(statement)),
        ("item_position", pure_integer(item)),
        (
            "resolved_module_path",
            pure_text(target_module_path) if resolved else PURE_ABSENT,
        ),
        (
            "resolved_namespace",
            pure_enumeration(namespace) if resolved else PURE_ABSENT,
        ),
        (
            "resolved_declaration_kind",
            pure_enumeration(declaration_kind) if resolved else PURE_ABSENT,
        ),
        (
            "resolved_declared_name",
            pure_text(exported_name) if resolved else PURE_ABSENT,
        ),
        ("issues", pure_integer(issues)),
    )


def _import_issue(
    index: int, request: int, issue: int, status: str
) -> ProjectPureRecord:
    """Build one ``import_issue`` record."""

    return _record(
        "import_issue",
        ("module", pure_integer(index)),
        ("request", pure_integer(request)),
        ("issue", pure_integer(issue)),
        ("status", pure_enumeration(status)),
    )


def _export(
    index: int,
    request: int,
    *,
    local_name: str,
    module_path: str,
    namespace: str = "type",
    declaration_kind: str = "shape",
    statement: int = 0,
    item: int = 0,
    exposed_name: str | None = None,
    entry_origin: str | None = "local_declaration",
    issues: int = 0,
) -> ProjectPureRecord:
    """Build one ``export`` record with or without a resolved facade entry."""

    resolved = entry_origin is not None
    exposed = local_name if exposed_name is None else exposed_name
    return _record(
        "export",
        ("module", pure_integer(index)),
        ("request", pure_integer(request)),
        ("local_name", pure_text(local_name)),
        ("namespace", pure_enumeration(namespace)),
        ("declaration_kind", pure_enumeration(declaration_kind)),
        ("module_statement_position", pure_integer(statement)),
        ("item_position", pure_integer(item)),
        ("exposed_name", pure_text(exposed) if resolved else PURE_ABSENT),
        (
            "entry_origin",
            pure_enumeration(entry_origin) if entry_origin is not None else PURE_ABSENT,
        ),
        ("target_module_path", pure_text(module_path) if resolved else PURE_ABSENT),
        (
            "target_namespace",
            pure_enumeration(namespace) if resolved else PURE_ABSENT,
        ),
        (
            "target_declaration_kind",
            pure_enumeration(declaration_kind) if resolved else PURE_ABSENT,
        ),
        ("target_declared_name", pure_text(local_name) if resolved else PURE_ABSENT),
        ("issues", pure_integer(issues)),
    )


def _export_issue(
    index: int, request: int, issue: int, status: str
) -> ProjectPureRecord:
    """Build one ``export_issue`` record."""

    return _record(
        "export_issue",
        ("module", pure_integer(index)),
        ("request", pure_integer(request)),
        ("issue", pure_integer(issue)),
        ("status", pure_enumeration(status)),
    )


def _declaration(
    index: int,
    declaration: int,
    *,
    owner_name: str,
    declared_name: str,
    namespace: str = "type",
    declaration_kind: str = "shape",
    availability: str = "absent",
    occurrence_count: int = 1,
    occurrence_index: int = 0,
    relation_status: str | None = None,
    relation_reason: str | None = None,
    row_fields: int = 0,
) -> ProjectPureRecord:
    """Build one ``declaration`` record."""

    return _record(
        "declaration",
        ("module", pure_integer(index)),
        ("declaration", pure_integer(declaration)),
        ("owner_kind", pure_enumeration("local_module")),
        ("owner_namespace", pure_text("")),
        ("owner_name", pure_text(owner_name)),
        ("namespace", pure_enumeration(namespace)),
        ("declaration_kind", pure_enumeration(declaration_kind)),
        ("declared_name", pure_text(declared_name)),
        ("availability", pure_enumeration(availability)),
        ("occurrence_count", pure_integer(occurrence_count)),
        ("occurrence_index", pure_integer(occurrence_index)),
        (
            "relation_status",
            pure_enumeration(relation_status)
            if relation_status is not None
            else PURE_ABSENT,
        ),
        (
            "relation_reason",
            pure_enumeration(relation_reason)
            if relation_reason is not None
            else PURE_ABSENT,
        ),
        ("row_fields", pure_integer(row_fields)),
    )


def _row_field(
    index: int,
    declaration: int,
    field: int,
    *,
    name: str,
    nullability: str = "non_null",
    result_role: str = "ordinary_row_value",
) -> ProjectPureRecord:
    """Build one ``declaration_row_field`` record."""

    return _record(
        "declaration_row_field",
        ("module", pure_integer(index)),
        ("declaration", pure_integer(declaration)),
        ("field", pure_integer(field)),
        ("name", pure_text(name)),
        ("nullability", pure_enumeration(nullability)),
        ("result_role", pure_enumeration(result_role)),
    )


def _origin(
    index: int,
    origin: int,
    *,
    local_name: str,
    target_module_path: str,
    target_declared_name: str,
    binding: str = "local_declaration",
    namespace: str = "type",
    declaration_kind: str = "shape",
    target_declaration_position: int = 0,
    hops: int = 0,
) -> ProjectPureRecord:
    """Build one ``origin`` record."""

    return _record(
        "origin",
        ("module", pure_integer(index)),
        ("origin", pure_integer(origin)),
        ("namespace", pure_enumeration(namespace)),
        ("declaration_kind", pure_enumeration(declaration_kind)),
        ("local_name", pure_text(local_name)),
        ("binding", pure_enumeration(binding)),
        ("target_module_path", pure_text(target_module_path)),
        ("target_declaration_position", pure_integer(target_declaration_position)),
        ("target_declared_name", pure_text(target_declared_name)),
        ("hops", pure_integer(hops)),
    )


def _origin_hop(
    index: int,
    origin: int,
    hop: int,
    *,
    module_path: str,
    exported_name: str,
    facade_origin: str = "local_declaration",
    target_module_path: str | None = None,
    target_declared_name: str | None = None,
) -> ProjectPureRecord:
    """Build one ``origin_hop`` record.

    Every hop of one chain names the same nominal target, which for an interior
    re-export hop is not the facade it passes through.
    """

    target_path = module_path if target_module_path is None else target_module_path
    target_name = (
        exported_name if target_declared_name is None else target_declared_name
    )
    return _record(
        "origin_hop",
        ("module", pure_integer(index)),
        ("origin", pure_integer(origin)),
        ("hop", pure_integer(hop)),
        ("import_target_module_path", pure_text(module_path)),
        ("import_exported_name", pure_text(exported_name)),
        ("import_module_statement_position", pure_integer(0)),
        ("import_item_position", pure_integer(0)),
        ("facade_module_path", pure_text(module_path)),
        ("facade_exposed_name", pure_text(exported_name)),
        ("facade_origin", pure_enumeration(facade_origin)),
        ("target_module_path", pure_text(target_path)),
        ("target_declared_name", pure_text(target_name)),
    )


def _dependency(
    index: int,
    dependency: int,
    *,
    kind: str,
    reference_role: str,
    owner_position: int = 0,
    member_position: int = 0,
    declaration_target: tuple[str, int, str] | None = None,
    row_field_target: tuple[int, str, int, str] | None = None,
) -> ProjectPureRecord:
    """Build one ``dependency`` record with at most one target kind."""

    return _record(
        "dependency",
        ("module", pure_integer(index)),
        ("dependency", pure_integer(dependency)),
        ("kind", pure_enumeration(kind)),
        ("reference_owner_declaration_position", pure_integer(owner_position)),
        ("reference_role", pure_enumeration(reference_role)),
        ("reference_member_position", pure_integer(member_position)),
        (
            "target_declaration_module_path",
            pure_text(declaration_target[0])
            if declaration_target is not None
            else PURE_ABSENT,
        ),
        (
            "target_declaration_position",
            pure_integer(declaration_target[1])
            if declaration_target is not None
            else PURE_ABSENT,
        ),
        (
            "target_declaration_declared_name",
            pure_text(declaration_target[2])
            if declaration_target is not None
            else PURE_ABSENT,
        ),
        (
            "target_row_field_owner_declaration_position",
            pure_integer(row_field_target[0])
            if row_field_target is not None
            else PURE_ABSENT,
        ),
        (
            "target_row_field_kind",
            pure_enumeration(row_field_target[1])
            if row_field_target is not None
            else PURE_ABSENT,
        ),
        (
            "target_row_field_position",
            pure_integer(row_field_target[2])
            if row_field_target is not None
            else PURE_ABSENT,
        ),
        (
            "target_row_field_name",
            pure_text(row_field_target[3])
            if row_field_target is not None
            else PURE_ABSENT,
        ),
    )


def _row_lineage(
    index: int,
    lineage: int,
    *,
    owner_position: int = 0,
    status: str = "concrete",
    reason: str = "direct_source_concrete",
    fields: int = 0,
) -> ProjectPureRecord:
    """Build one ``row_lineage`` record."""

    return _record(
        "row_lineage",
        ("module", pure_integer(index)),
        ("lineage", pure_integer(lineage)),
        ("owner_declaration_position", pure_integer(owner_position)),
        ("status", pure_enumeration(status)),
        ("reason", pure_enumeration(reason)),
        ("fields", pure_integer(fields)),
    )


def _lineage_field(
    index: int,
    lineage: int,
    field: int,
    *,
    name: str,
    kind: str = "relation_output",
    field_position: int = 0,
    paths: int = 0,
) -> ProjectPureRecord:
    """Build one ``row_lineage_field`` record."""

    return _record(
        "row_lineage_field",
        ("module", pure_integer(index)),
        ("lineage", pure_integer(lineage)),
        ("field", pure_integer(field)),
        ("kind", pure_enumeration(kind)),
        ("field_position", pure_integer(field_position)),
        ("name", pure_text(name)),
        ("paths", pure_integer(paths)),
    )


def _lineage_path(
    index: int,
    lineage: int,
    field: int,
    path: int,
    *,
    root_module_path: str,
    root_field_name: str,
    root_owner_position: int = 0,
    root_field_position: int = 0,
    hops: int = 0,
) -> ProjectPureRecord:
    """Build one ``row_lineage_path`` record."""

    return _record(
        "row_lineage_path",
        ("module", pure_integer(index)),
        ("lineage", pure_integer(lineage)),
        ("field", pure_integer(field)),
        ("path", pure_integer(path)),
        ("root_module_path", pure_text(root_module_path)),
        ("root_owner_declaration_position", pure_integer(root_owner_position)),
        ("root_field_position", pure_integer(root_field_position)),
        ("root_field_name", pure_text(root_field_name)),
        ("hops", pure_integer(hops)),
    )


def _lineage_hop(
    index: int,
    lineage: int,
    field: int,
    path: int,
    hop: int,
    *,
    projection_kind: str,
    output_field_name: str,
    upstream_field_name: str,
) -> ProjectPureRecord:
    """Build one ``row_lineage_hop`` record."""

    return _record(
        "row_lineage_hop",
        ("module", pure_integer(index)),
        ("lineage", pure_integer(lineage)),
        ("field", pure_integer(field)),
        ("path", pure_integer(path)),
        ("hop", pure_integer(hop)),
        ("projection_kind", pure_enumeration(projection_kind)),
        ("output_field_name", pure_text(output_field_name)),
        ("upstream_field_name", pure_text(upstream_field_name)),
    )


def _type_resolution(
    index: int,
    resolution: int,
    *,
    canonical_name: str,
    owner_position: int = 0,
    role: str = "shape_field_type",
    member_position: int = 0,
    direct_kind: str = "builtin",
    canonical_kind: str = "builtin",
    canonical_target: tuple[str, str] | None = None,
    alias_chain: int = 0,
) -> ProjectPureRecord:
    """Build one ``type_resolution`` record."""

    return _record(
        "type_resolution",
        ("module", pure_integer(index)),
        ("resolution", pure_integer(resolution)),
        ("owner_declaration_position", pure_integer(owner_position)),
        ("role", pure_enumeration(role)),
        ("member_position", pure_integer(member_position)),
        ("direct_kind", pure_enumeration(direct_kind)),
        ("canonical_kind", pure_enumeration(canonical_kind)),
        ("canonical_name", pure_text(canonical_name)),
        (
            "canonical_target_module_path",
            pure_text(canonical_target[0])
            if canonical_target is not None
            else PURE_ABSENT,
        ),
        (
            "canonical_target_declared_name",
            pure_text(canonical_target[1])
            if canonical_target is not None
            else PURE_ABSENT,
        ),
        ("alias_chain", pure_integer(alias_chain)),
    )


def _type_alias(
    index: int,
    resolution: int,
    alias: int,
    *,
    module_path: str,
    declared_name: str,
) -> ProjectPureRecord:
    """Build one ``type_resolution_alias`` record."""

    return _record(
        "type_resolution_alias",
        ("module", pure_integer(index)),
        ("resolution", pure_integer(resolution)),
        ("alias", pure_integer(alias)),
        ("module_path", pure_text(module_path)),
        ("namespace", pure_enumeration("type")),
        ("declaration_kind", pure_enumeration("type")),
        ("declared_name", pure_text(declared_name)),
    )


def _source_shape_resolution(
    index: int,
    resolution: int,
    *,
    owner_position: int,
    target_module_path: str,
    target_declared_name: str,
) -> ProjectPureRecord:
    """Build one ``source_shape_resolution`` record."""

    return _record(
        "source_shape_resolution",
        ("module", pure_integer(index)),
        ("resolution", pure_integer(resolution)),
        ("owner_declaration_position", pure_integer(owner_position)),
        ("target_module_path", pure_text(target_module_path)),
        ("target_declared_name", pure_text(target_declared_name)),
    )


def _relation_resolution(
    index: int,
    resolution: int,
    *,
    owner_position: int,
    local_name: str,
    target_module_path: str,
    target_declared_name: str,
) -> ProjectPureRecord:
    """Build one ``relation_resolution`` record."""

    return _record(
        "relation_resolution",
        ("module", pure_integer(index)),
        ("resolution", pure_integer(resolution)),
        ("owner_declaration_position", pure_integer(owner_position)),
        ("local_name", pure_text(local_name)),
        ("target_module_path", pure_text(target_module_path)),
        ("target_declared_name", pure_text(target_declared_name)),
    )


def _semantic_facts(
    index: int,
    facts: int,
    *,
    owner_position: int = 0,
    status: str = "concrete",
    reason: str = "direct_source_concrete",
    let_bindings: int = 0,
    selects: int = 0,
    clause_dependencies: int = 0,
    window_outputs: int = 0,
) -> ProjectPureRecord:
    """Build one ``semantic_facts`` record."""

    return _record(
        "semantic_facts",
        ("module", pure_integer(index)),
        ("facts", pure_integer(facts)),
        ("owner_declaration_position", pure_integer(owner_position)),
        ("status", pure_enumeration(status)),
        ("reason", pure_enumeration(reason)),
        ("let_bindings", pure_integer(let_bindings)),
        ("selects", pure_integer(selects)),
        ("clause_dependencies", pure_integer(clause_dependencies)),
        ("window_outputs", pure_integer(window_outputs)),
    )


def _let_binding(
    index: int,
    facts: int,
    binding: int,
    *,
    binding_ordinal: int,
    has_value_type: bool,
) -> ProjectPureRecord:
    """Build one ``semantic_let_binding`` record."""

    return _record(
        "semantic_let_binding",
        ("module", pure_integer(index)),
        ("facts", pure_integer(facts)),
        ("binding", pure_integer(binding)),
        ("binding_ordinal", pure_integer(binding_ordinal)),
        ("has_value_type", pure_boolean(has_value_type)),
    )


def _select(
    index: int,
    facts: int,
    select: int,
    *,
    selected_output_ordinal: int,
    output_name: str | None,
) -> ProjectPureRecord:
    """Build one ``semantic_select`` record."""

    return _record(
        "semantic_select",
        ("module", pure_integer(index)),
        ("facts", pure_integer(facts)),
        ("select", pure_integer(select)),
        ("selected_output_ordinal", pure_integer(selected_output_ordinal)),
        (
            "output_name",
            pure_text(output_name) if output_name is not None else PURE_ABSENT,
        ),
    )


def _clause_dependency(
    index: int,
    facts: int,
    dependency: int,
    *,
    role: str,
    source_ordinal: int,
    status: str,
) -> ProjectPureRecord:
    """Build one ``semantic_clause_dependency`` record."""

    return _record(
        "semantic_clause_dependency",
        ("module", pure_integer(index)),
        ("facts", pure_integer(facts)),
        ("dependency", pure_integer(dependency)),
        ("role", pure_enumeration(role)),
        ("source_ordinal", pure_integer(source_ordinal)),
        ("status", pure_enumeration(status)),
    )


def _window_output(
    index: int,
    facts: int,
    output: int,
    *,
    selected_output_ordinal: int,
    output_name: str | None,
    status: str,
) -> ProjectPureRecord:
    """Build one ``semantic_window_output`` record."""

    return _record(
        "semantic_window_output",
        ("module", pure_integer(index)),
        ("facts", pure_integer(facts)),
        ("output", pure_integer(output)),
        ("selected_output_ordinal", pure_integer(selected_output_ordinal)),
        (
            "output_name",
            pure_text(output_name) if output_name is not None else PURE_ABSENT,
        ),
        ("status", pure_enumeration(status)),
    )


def _issue(
    index: int,
    issue: int,
    *,
    family: str,
    status: str,
    local_name: str | None = None,
) -> ProjectPureRecord:
    """Build one ``issue`` record."""

    return _record(
        "issue",
        ("module", pure_integer(index)),
        ("issue", pure_integer(issue)),
        ("family", pure_enumeration(family)),
        ("status", pure_text(status)),
        (
            "local_name",
            pure_text(local_name) if local_name is not None else PURE_ABSENT,
        ),
    )


_SURROGATE_PATH = "bad\udcff.pietto"

_CONTROL_TEXT = "a\\b\tc\nd\re\x00f\x1fg\x7fh"

_NON_ASCII_PATH = "模块é.pietto"


def _accepted(
    vector_id: str,
    purpose: DifferentialPurpose,
    document: ProjectPureDocument,
) -> DifferentialVector:
    """Build one accepted vector whose expected payload is stored below."""

    return DifferentialVector(
        vector_format=DIFFERENTIAL_VECTOR_FORMAT,
        vector_id=vector_id,
        purpose=purpose,
        classification=_EVALUATION,
        document=document,
        expected_status=ProjectPureStatus.OK,
        expected_bytes=EXPECTED_CANONICAL_BYTES[vector_id],
    )


def _rejected(
    vector_id: str,
    purpose: DifferentialPurpose,
    document: ProjectPureDocument,
    status: ProjectPureStatus,
    record_position: int | None = None,
    field_position: int | None = None,
) -> DifferentialVector:
    """Build one rejected vector with its exact normalized expectation."""

    return DifferentialVector(
        vector_format=DIFFERENTIAL_VECTOR_FORMAT,
        vector_id=vector_id,
        purpose=purpose,
        classification=_REJECTION,
        document=document,
        expected_status=status,
        expected_record_position=record_position,
        expected_field_position=field_position,
    )


# Reviewed expected payloads. This block is authority: it is authored once
# through the harness proposal path, reviewed by hand, and never regenerated
# during normal validation.
_EXPECTED_CANONICAL_BYTES_LITERAL: dict[str, bytes] = {
    "empty_project": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:0\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\n",
    "single_module": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\n",
    "several_modules": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:3\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nmodule\tmodule=i:1\tpath=s:b.pietto\ndigest\tmodule=i:1\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:1\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:1\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:1\tmember=i:0\tpath=s:b.pietto\nmodule\tmodule=i:2\tpath=s:c.pietto\ndigest\tmodule=i:2\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:2\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:2\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:2\tmember=i:0\tpath=s:c.pietto\n",
    "declaration_order_and_multiplicity": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:First\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:1\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Second\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:2\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Third\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\n",
    "same_spelling_distinct_modules": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:2\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\nmodule\tmodule=i:1\tpath=s:b.pietto\ndigest\tmodule=i:1\talgorithm=e:sha256_opened_bytes\tdigest=s:2222222222222222222222222222222222222222222222222222222222222222\tbyte_count=i:12\nreadiness\tmodule=i:1\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:1\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:1\tmember=i:0\tpath=s:b.pietto\ndeclaration\tmodule=i:1\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:b.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\n",
    "same_spelling_distinct_namespaces": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:1\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:table\tdeclared_name=s:Row\tavailability=e:concrete\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=e:concrete\trelation_reason=e:direct_source_concrete\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:2\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:callable\tdeclaration_kind=e:derive\tdeclared_name=s:Row\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\n",
    "alias_distinct_from_target": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nimport\tmodule=i:0\trequest=i:0\tlocal_name=s:Local\tnamespace=e:type\tdeclaration_kind=e:shape\ttarget_module_path=s:b.pietto\texported_name=s:Exported\tmodule_statement_position=i:0\titem_position=i:0\tresolved_module_path=s:b.pietto\tresolved_namespace=e:type\tresolved_declaration_kind=e:shape\tresolved_declared_name=s:Exported\tissues=i:0\n",
    "two_aliases_one_target": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nimport\tmodule=i:0\trequest=i:0\tlocal_name=s:First\tnamespace=e:type\tdeclaration_kind=e:shape\ttarget_module_path=s:b.pietto\texported_name=s:Row\tmodule_statement_position=i:0\titem_position=i:0\tresolved_module_path=s:b.pietto\tresolved_namespace=e:type\tresolved_declaration_kind=e:shape\tresolved_declared_name=s:Row\tissues=i:0\nimport\tmodule=i:0\trequest=i:1\tlocal_name=s:Second\tnamespace=e:type\tdeclaration_kind=e:shape\ttarget_module_path=s:b.pietto\texported_name=s:Row\tmodule_statement_position=i:0\titem_position=i:1\tresolved_module_path=s:b.pietto\tresolved_namespace=e:type\tresolved_declaration_kind=e:shape\tresolved_declared_name=s:Row\tissues=i:0\n",
    "explicit_reexport": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nexport\tmodule=i:0\trequest=i:0\tlocal_name=s:Row\tnamespace=e:type\tdeclaration_kind=e:shape\tmodule_statement_position=i:0\titem_position=i:0\texposed_name=s:Row\tentry_origin=e:explicit_reexport\ttarget_module_path=s:b.pietto\ttarget_namespace=e:type\ttarget_declaration_kind=e:shape\ttarget_declared_name=s:Row\tissues=i:0\norigin\tmodule=i:0\torigin=i:0\tnamespace=e:type\tdeclaration_kind=e:shape\tlocal_name=s:Row\tbinding=e:imported_binding\ttarget_module_path=s:c.pietto\ttarget_declaration_position=i:0\ttarget_declared_name=s:Row\thops=i:2\norigin_hop\tmodule=i:0\torigin=i:0\thop=i:0\timport_target_module_path=s:b.pietto\timport_exported_name=s:Row\timport_module_statement_position=i:0\timport_item_position=i:0\tfacade_module_path=s:b.pietto\tfacade_exposed_name=s:Row\tfacade_origin=e:explicit_reexport\ttarget_module_path=s:c.pietto\ttarget_declared_name=s:Row\norigin_hop\tmodule=i:0\torigin=i:0\thop=i:1\timport_target_module_path=s:c.pietto\timport_exported_name=s:Row\timport_module_statement_position=i:0\timport_item_position=i:0\tfacade_module_path=s:c.pietto\tfacade_exposed_name=s:Row\tfacade_origin=e:local_declaration\ttarget_module_path=s:c.pietto\ttarget_declared_name=s:Row\n",
    "availability_states": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:table\tdeclared_name=s:R0\tavailability=e:concrete\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=e:concrete\trelation_reason=e:direct_source_concrete\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:1\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:table\tdeclared_name=s:R1\tavailability=e:unknown\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=e:unknown\trelation_reason=e:unknown_schema\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:2\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:table\tdeclared_name=s:R2\tavailability=e:deferred\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=e:deferred\trelation_reason=e:aggregate_grouped_deferred\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:3\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:table\tdeclared_name=s:R3\tavailability=e:blocked\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=e:blocked\trelation_reason=e:unresolved_relation_blocked\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:4\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:table\tdeclared_name=s:R4\tavailability=e:ambiguous\toccurrence_count=i:2\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:5\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:table\tdeclared_name=s:R4\tavailability=e:ambiguous\toccurrence_count=i:2\toccurrence_index=i:1\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:6\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:T0\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:7\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:T1\tavailability=e:ambiguous\toccurrence_count=i:2\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:8\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:T1\tavailability=e:ambiguous\toccurrence_count=i:2\toccurrence_index=i:1\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\n",
    "module_cycle_and_blocked_readiness": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:blocked\treason=e:module_cycle_blocked\tcycles=i:1\nreadiness_cycle\tmodule=i:0\tcycle=i:0\tmembers=i:2\nreadiness_cycle_member\tmodule=i:0\tcycle=i:0\tmember=i:0\tpath=s:a.pietto\nreadiness_cycle_member\tmodule=i:0\tcycle=i:0\tmember=i:1\tpath=s:b.pietto\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:true\tcomponent_members=i:2\tdependency_targets=i:1\timport_evidence=i:1\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ngraph_component_member\tmodule=i:0\tmember=i:1\tpath=s:b.pietto\ngraph_dependency_target\tmodule=i:0\ttarget=i:0\tpath=s:b.pietto\ngraph_import_evidence\tmodule=i:0\tevidence=i:0\tpath=s:b.pietto\tmodule_statement_position=i:0\titem_position=i:0\n",
    "duplicate_nominal_identity_bucket": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:2\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:1\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:2\toccurrence_index=i:1\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\n",
    "equal_digest_distinct_modules": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:2\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nmodule\tmodule=i:1\tpath=s:b.pietto\ndigest\tmodule=i:1\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:1\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:1\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:1\tmember=i:0\tpath=s:b.pietto\n",
    "direct_and_renamed_lineage": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nrow_lineage\tmodule=i:0\tlineage=i:0\towner_declaration_position=i:0\tstatus=e:concrete\treason=e:direct_source_concrete\tfields=i:2\nrow_lineage_field\tmodule=i:0\tlineage=i:0\tfield=i:0\tkind=e:relation_output\tfield_position=i:0\tname=s:id\tpaths=i:1\nrow_lineage_path\tmodule=i:0\tlineage=i:0\tfield=i:0\tpath=i:0\troot_module_path=s:b.pietto\troot_owner_declaration_position=i:0\troot_field_position=i:0\troot_field_name=s:id\thops=i:1\nrow_lineage_hop\tmodule=i:0\tlineage=i:0\tfield=i:0\tpath=i:0\thop=i:0\tprojection_kind=e:direct\toutput_field_name=s:id\tupstream_field_name=s:id\nrow_lineage_field\tmodule=i:0\tlineage=i:0\tfield=i:1\tkind=e:relation_output\tfield_position=i:1\tname=s:total\tpaths=i:1\nrow_lineage_path\tmodule=i:0\tlineage=i:0\tfield=i:1\tpath=i:0\troot_module_path=s:b.pietto\troot_owner_declaration_position=i:0\troot_field_position=i:1\troot_field_name=s:amount\thops=i:1\nrow_lineage_hop\tmodule=i:0\tlineage=i:0\tfield=i:1\tpath=i:0\thop=i:0\tprojection_kind=e:renamed\toutput_field_name=s:total\tupstream_field_name=s:amount\n",
    "preserved_semantic_facts": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nsemantic_facts\tmodule=i:0\tfacts=i:0\towner_declaration_position=i:0\tstatus=e:concrete\treason=e:direct_source_concrete\tlet_bindings=i:1\tselects=i:2\tclause_dependencies=i:2\twindow_outputs=i:2\nsemantic_let_binding\tmodule=i:0\tfacts=i:0\tbinding=i:0\tbinding_ordinal=i:0\thas_value_type=b:true\nsemantic_select\tmodule=i:0\tfacts=i:0\tselect=i:0\tselected_output_ordinal=i:0\toutput_name=s:id\nsemantic_select\tmodule=i:0\tfacts=i:0\tselect=i:1\tselected_output_ordinal=i:1\toutput_name=n:\nsemantic_clause_dependency\tmodule=i:0\tfacts=i:0\tdependency=i:0\trole=e:group_key\tsource_ordinal=i:0\tstatus=e:concrete\nsemantic_clause_dependency\tmodule=i:0\tfacts=i:0\tdependency=i:1\trole=e:grouped_order\tsource_ordinal=i:0\tstatus=e:ambiguous\nsemantic_window_output\tmodule=i:0\tfacts=i:0\toutput=i:0\tselected_output_ordinal=i:1\toutput_name=s:rank\tstatus=e:deferred\nsemantic_window_output\tmodule=i:0\tfacts=i:0\toutput=i:1\tselected_output_ordinal=i:2\toutput_name=n:\tstatus=e:unknown\n",
    "nullability_and_result_role": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:relation\tdeclaration_kind=e:query\tdeclared_name=s:result\tavailability=e:concrete\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=e:concrete\trelation_reason=e:direct_source_concrete\trow_fields=i:4\ndeclaration_row_field\tmodule=i:0\tdeclaration=i:0\tfield=i:0\tname=s:id\tnullability=e:non_null\tresult_role=e:ordinary_row_value\ndeclaration_row_field\tmodule=i:0\tdeclaration=i:0\tfield=i:1\tname=s:category\tnullability=e:nullable\tresult_role=e:group_key\ndeclaration_row_field\tmodule=i:0\tdeclaration=i:0\tfield=i:2\tname=s:total\tnullability=e:unknown\tresult_role=e:aggregate_result\ndeclaration_row_field\tmodule=i:0\tdeclaration=i:0\tfield=i:3\tname=s:rank\tnullability=e:non_null\tresult_role=e:window_result\n",
    "surrogate_text": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:bad\\udcff.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:bad\\udcff.pietto\n",
    "control_character_text": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:a\\\\b\\tc\\nd\\re\\x00f\\x1fg\\x7fh\tavailability=e:absent\toccurrence_count=i:1\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\n",
    "non_ascii_text": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:\xe6\xa8\xa1\xe5\x9d\x97\xc3\xa9.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:\xe6\xa8\xa1\xe5\x9d\x97\xc3\xa9.pietto\n",
    "absent_versus_empty_text": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nexport\tmodule=i:0\trequest=i:0\tlocal_name=s:Row\tnamespace=e:type\tdeclaration_kind=e:shape\tmodule_statement_position=i:0\titem_position=i:0\texposed_name=s:Row\tentry_origin=e:local_declaration\ttarget_module_path=s:a.pietto\ttarget_namespace=e:type\ttarget_declaration_kind=e:shape\ttarget_declared_name=s:Row\tissues=i:0\nexport\tmodule=i:0\trequest=i:1\tlocal_name=s:Missing\tnamespace=e:type\tdeclaration_kind=e:shape\tmodule_statement_position=i:0\titem_position=i:1\texposed_name=n:\tentry_origin=n:\ttarget_module_path=n:\ttarget_namespace=n:\ttarget_declaration_kind=n:\ttarget_declared_name=n:\tissues=i:1\nexport_issue\tmodule=i:0\trequest=i:1\tissue=i:0\tstatus=e:unresolved_export_binding\nissue\tmodule=i:0\tissue=i:0\tfamily=e:graph\tstatus=s:module_import_cycle\tlocal_name=n:\nissue\tmodule=i:0\tissue=i:1\tfamily=e:relation\tstatus=s:unknown_relation_reference\tlocal_name=s:\n",
    "boundary_cardinalities": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:blocked\treason=e:module_cycle_blocked\tcycles=i:3\nreadiness_cycle\tmodule=i:0\tcycle=i:0\tmembers=i:3\nreadiness_cycle_member\tmodule=i:0\tcycle=i:0\tmember=i:0\tpath=s:a.pietto\nreadiness_cycle_member\tmodule=i:0\tcycle=i:0\tmember=i:1\tpath=s:b.pietto\nreadiness_cycle_member\tmodule=i:0\tcycle=i:0\tmember=i:2\tpath=s:c.pietto\nreadiness_cycle\tmodule=i:0\tcycle=i:1\tmembers=i:3\nreadiness_cycle_member\tmodule=i:0\tcycle=i:1\tmember=i:0\tpath=s:a.pietto\nreadiness_cycle_member\tmodule=i:0\tcycle=i:1\tmember=i:1\tpath=s:b.pietto\nreadiness_cycle_member\tmodule=i:0\tcycle=i:1\tmember=i:2\tpath=s:c.pietto\nreadiness_cycle\tmodule=i:0\tcycle=i:2\tmembers=i:3\nreadiness_cycle_member\tmodule=i:0\tcycle=i:2\tmember=i:0\tpath=s:a.pietto\nreadiness_cycle_member\tmodule=i:0\tcycle=i:2\tmember=i:1\tpath=s:b.pietto\nreadiness_cycle_member\tmodule=i:0\tcycle=i:2\tmember=i:2\tpath=s:c.pietto\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:true\tcomponent_members=i:3\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ngraph_component_member\tmodule=i:0\tmember=i:1\tpath=s:b.pietto\ngraph_component_member\tmodule=i:0\tmember=i:2\tpath=s:c.pietto\n",
    "large_repeated_bucket": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndeclaration\tmodule=i:0\tdeclaration=i:0\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:6\toccurrence_index=i:0\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:1\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:6\toccurrence_index=i:1\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:2\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:6\toccurrence_index=i:2\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:3\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:6\toccurrence_index=i:3\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:4\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:6\toccurrence_index=i:4\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\ndeclaration\tmodule=i:0\tdeclaration=i:5\towner_kind=e:local_module\towner_namespace=s:\towner_name=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:shape\tdeclared_name=s:Row\tavailability=e:ambiguous\toccurrence_count=i:6\toccurrence_index=i:5\trelation_status=n:\trelation_reason=n:\trow_fields=i:0\n",
    "issue_families": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nissue\tmodule=i:0\tissue=i:0\tfamily=e:graph\tstatus=s:unresolved_target_module\tlocal_name=n:\nissue\tmodule=i:0\tissue=i:1\tfamily=e:type_source\tstatus=s:ambiguous_local_type_name\tlocal_name=s:Row\nissue\tmodule=i:0\tissue=i:2\tfamily=e:relation\tstatus=s:local_relation_cycle\tlocal_name=s:rows\n",
    "type_alias_chain": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ntype_resolution\tmodule=i:0\tresolution=i:0\towner_declaration_position=i:0\trole=e:shape_field_type\tmember_position=i:0\tdirect_kind=e:type\tcanonical_kind=e:builtin\tcanonical_name=s:Int\tcanonical_target_module_path=n:\tcanonical_target_declared_name=n:\talias_chain=i:2\ntype_resolution_alias\tmodule=i:0\tresolution=i:0\talias=i:0\tmodule_path=s:a.pietto\tnamespace=e:type\tdeclaration_kind=e:type\tdeclared_name=s:Years\ntype_resolution_alias\tmodule=i:0\tresolution=i:0\talias=i:1\tmodule_path=s:b.pietto\tnamespace=e:type\tdeclaration_kind=e:type\tdeclared_name=s:Age\ntype_resolution\tmodule=i:0\tresolution=i:1\towner_declaration_position=i:0\trole=e:shape_field_type\tmember_position=i:1\tdirect_kind=e:builtin\tcanonical_kind=e:builtin\tcanonical_name=s:Text\tcanonical_target_module_path=n:\tcanonical_target_declared_name=n:\talias_chain=i:0\n",
    "issue_buckets": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nimport\tmodule=i:0\trequest=i:0\tlocal_name=s:Row\tnamespace=e:type\tdeclaration_kind=e:shape\ttarget_module_path=s:b.pietto\texported_name=s:Row\tmodule_statement_position=i:0\titem_position=i:0\tresolved_module_path=n:\tresolved_namespace=n:\tresolved_declaration_kind=n:\tresolved_declared_name=n:\tissues=i:2\nimport_issue\tmodule=i:0\trequest=i:0\tissue=i:0\tstatus=e:unresolved_target_module\nimport_issue\tmodule=i:0\trequest=i:0\tissue=i:1\tstatus=e:duplicate_source_request\nexport\tmodule=i:0\trequest=i:0\tlocal_name=s:Row\tnamespace=e:type\tdeclaration_kind=e:shape\tmodule_statement_position=i:0\titem_position=i:0\texposed_name=n:\tentry_origin=n:\ttarget_module_path=n:\ttarget_namespace=n:\ttarget_declaration_kind=n:\ttarget_declared_name=n:\tissues=i:2\nexport_issue\tmodule=i:0\trequest=i:0\tissue=i:0\tstatus=e:ambiguous_local_declaration\nexport_issue\tmodule=i:0\trequest=i:0\tissue=i:1\tstatus=e:ambiguous_candidate_set\n",
    "dependency_target_variants": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ndependency\tmodule=i:0\tdependency=i:0\tkind=e:source_shape_reference\treference_owner_declaration_position=i:0\treference_role=e:source_shape\treference_member_position=i:0\ttarget_declaration_module_path=s:b.pietto\ttarget_declaration_position=i:0\ttarget_declaration_declared_name=s:Row\ttarget_row_field_owner_declaration_position=n:\ttarget_row_field_kind=n:\ttarget_row_field_position=n:\ttarget_row_field_name=n:\ndependency\tmodule=i:0\tdependency=i:1\tkind=e:row_field_reference\treference_owner_declaration_position=i:0\treference_role=e:row_field\treference_member_position=i:1\ttarget_declaration_module_path=n:\ttarget_declaration_position=n:\ttarget_declaration_declared_name=n:\ttarget_row_field_owner_declaration_position=i:1\ttarget_row_field_kind=e:source_field\ttarget_row_field_position=i:0\ttarget_row_field_name=s:id\ndependency\tmodule=i:0\tdependency=i:2\tkind=e:relation_reference\treference_owner_declaration_position=i:0\treference_role=e:relation_from\treference_member_position=i:2\ttarget_declaration_module_path=s:b.pietto\ttarget_declaration_position=i:1\ttarget_declaration_declared_name=s:rows\ttarget_row_field_owner_declaration_position=n:\ttarget_row_field_kind=n:\ttarget_row_field_position=n:\ttarget_row_field_name=n:\n",
    "boolean_values": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:true\tcomponent_members=i:1\tdependency_targets=i:1\timport_evidence=i:1\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ngraph_dependency_target\tmodule=i:0\ttarget=i:0\tpath=s:a.pietto\ngraph_import_evidence\tmodule=i:0\tevidence=i:0\tpath=s:a.pietto\tmodule_statement_position=i:0\titem_position=i:0\nsemantic_facts\tmodule=i:0\tfacts=i:0\towner_declaration_position=i:0\tstatus=e:concrete\treason=e:direct_source_concrete\tlet_bindings=i:2\tselects=i:0\tclause_dependencies=i:0\twindow_outputs=i:0\nsemantic_let_binding\tmodule=i:0\tfacts=i:0\tbinding=i:0\tbinding_ordinal=i:0\thas_value_type=b:true\nsemantic_let_binding\tmodule=i:0\tfacts=i:0\tbinding=i:1\tbinding_ordinal=i:1\thas_value_type=b:false\n",
    "resolution_sections": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\ntype_resolution\tmodule=i:0\tresolution=i:0\towner_declaration_position=i:0\trole=e:shape_field_type\tmember_position=i:0\tdirect_kind=e:builtin\tcanonical_kind=e:builtin\tcanonical_name=s:Int\tcanonical_target_module_path=n:\tcanonical_target_declared_name=n:\talias_chain=i:0\nsource_shape_resolution\tmodule=i:0\tresolution=i:0\towner_declaration_position=i:1\ttarget_module_path=s:b.pietto\ttarget_declared_name=s:Row\nsource_shape_resolution\tmodule=i:0\tresolution=i:1\towner_declaration_position=i:2\ttarget_module_path=s:b.pietto\ttarget_declared_name=s:Row\nrelation_resolution\tmodule=i:0\tresolution=i:0\towner_declaration_position=i:3\tlocal_name=s:rows\ttarget_module_path=s:b.pietto\ttarget_declared_name=s:rows\nrelation_resolution\tmodule=i:0\tresolution=i:1\towner_declaration_position=i:4\tlocal_name=s:r\ttarget_module_path=s:b.pietto\ttarget_declared_name=s:rows\n",
    "unresolved_import": b"inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:1\nowner\tkind=e:local_project_root\tnamespace=s:\tname=s:\nmodule\tmodule=i:0\tpath=s:a.pietto\ndigest\tmodule=i:0\talgorithm=e:sha256_opened_bytes\tdigest=s:1111111111111111111111111111111111111111111111111111111111111111\tbyte_count=i:12\nreadiness\tmodule=i:0\tstatus=e:ready\treason=e:trusted_local_source_resolved\tcycles=i:0\ngraph\tmodule=i:0\tcomponent_is_cyclic=b:false\tcomponent_members=i:1\tdependency_targets=i:0\timport_evidence=i:0\ngraph_component_member\tmodule=i:0\tmember=i:0\tpath=s:a.pietto\nimport\tmodule=i:0\trequest=i:0\tlocal_name=s:Row\tnamespace=e:type\tdeclaration_kind=e:shape\ttarget_module_path=s:missing.pietto\texported_name=s:Row\tmodule_statement_position=i:0\titem_position=i:0\tresolved_module_path=n:\tresolved_namespace=n:\tresolved_declaration_kind=n:\tresolved_declared_name=n:\tissues=i:1\nimport_issue\tmodule=i:0\trequest=i:0\tissue=i:0\tstatus=e:unresolved_target_module\n",
}


def _pairs(
    documents: dict[str, tuple[DifferentialPurpose, ProjectPureDocument]],
) -> tuple[tuple[str, DifferentialPurpose, ProjectPureDocument], ...]:
    """Flatten the declared accepted documents into ordered identifier triples."""

    return tuple(
        (vector_id, purpose, document)
        for vector_id, (purpose, document) in documents.items()
    )


EXPECTED_CANONICAL_BYTES: Mapping[str, bytes] = MappingProxyType(
    _EXPECTED_CANONICAL_BYTES_LITERAL
)


def _accepted_documents() -> tuple[
    tuple[str, DifferentialPurpose, ProjectPureDocument], ...
]:
    """Return every accepted vector's identifier, purpose, and document.

    Ordered triples rather than a mapping, so a duplicate identifier reaches the
    harness's fail-closed check instead of being folded away silently.
    """

    return _pairs(_accepted_document_map())


_AVAILABILITY_STATE_ROWS: tuple[
    tuple[str, str, str, int, int, str | None, str | None], ...
] = (
    ("R0", "relation", "concrete", 1, 0, "concrete", "direct_source_concrete"),
    ("R1", "relation", "unknown", 1, 0, "unknown", "unknown_schema"),
    ("R2", "relation", "deferred", 1, 0, "deferred", "aggregate_grouped_deferred"),
    ("R3", "relation", "blocked", 1, 0, "blocked", "unresolved_relation_blocked"),
    ("R4", "relation", "ambiguous", 2, 0, None, None),
    ("R4", "relation", "ambiguous", 2, 1, None, None),
    ("T0", "type", "absent", 1, 0, None, None),
    ("T1", "type", "ambiguous", 2, 0, None, None),
    ("T1", "type", "ambiguous", 2, 1, None, None),
)


def _accepted_document_map() -> dict[
    str, tuple[DifferentialPurpose, ProjectPureDocument]
]:
    """Return the declared accepted documents in their exact declared order."""

    return {
        "empty_project": (
            DifferentialPurpose.EMPTY_PROJECT,
            _document(_header(0), _OWNER),
        ),
        "single_module": (
            DifferentialPurpose.SINGLE_MODULE,
            _document(_header(1), _OWNER, *_module_block(0, "a.pietto")),
        ),
        "several_modules": (
            DifferentialPurpose.SEVERAL_MODULES,
            _document(
                _header(3),
                _OWNER,
                *_module_block(0, "a.pietto"),
                *_module_block(1, "b.pietto"),
                *_module_block(2, "c.pietto"),
            ),
        ),
        "declaration_order_and_multiplicity": (
            DifferentialPurpose.DECLARATION_ORDER_AND_MULTIPLICITY,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _declaration(0, 0, owner_name="a.pietto", declared_name="First"),
                _declaration(0, 1, owner_name="a.pietto", declared_name="Second"),
                _declaration(0, 2, owner_name="a.pietto", declared_name="Third"),
            ),
        ),
        "same_spelling_distinct_modules": (
            DifferentialPurpose.SAME_SPELLING_DISTINCT_MODULES,
            _document(
                _header(2),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _declaration(0, 0, owner_name="a.pietto", declared_name="Row"),
                *_module_block(1, "b.pietto", digest=_DIGEST_B),
                _declaration(1, 0, owner_name="b.pietto", declared_name="Row"),
            ),
        ),
        "same_spelling_distinct_namespaces": (
            DifferentialPurpose.SAME_SPELLING_DISTINCT_NAMESPACES,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _declaration(0, 0, owner_name="a.pietto", declared_name="Row"),
                _declaration(
                    0,
                    1,
                    owner_name="a.pietto",
                    declared_name="Row",
                    namespace="relation",
                    declaration_kind="table",
                    availability="concrete",
                    relation_status="concrete",
                    relation_reason="direct_source_concrete",
                ),
                _declaration(
                    0,
                    2,
                    owner_name="a.pietto",
                    declared_name="Row",
                    namespace="callable",
                    declaration_kind="derive",
                ),
            ),
        ),
        "alias_distinct_from_target": (
            DifferentialPurpose.ALIAS_DISTINCT_FROM_TARGET,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _import(
                    0,
                    0,
                    local_name="Local",
                    exported_name="Exported",
                    target_module_path="b.pietto",
                ),
            ),
        ),
        "two_aliases_one_target": (
            DifferentialPurpose.TWO_ALIASES_ONE_TARGET,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _import(
                    0,
                    0,
                    local_name="First",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    item=0,
                ),
                _import(
                    0,
                    1,
                    local_name="Second",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    item=1,
                ),
            ),
        ),
        "explicit_reexport": (
            DifferentialPurpose.EXPLICIT_REEXPORT,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _export(
                    0,
                    0,
                    local_name="Row",
                    module_path="b.pietto",
                    entry_origin="explicit_reexport",
                ),
                _origin(
                    0,
                    0,
                    local_name="Row",
                    target_module_path="c.pietto",
                    target_declared_name="Row",
                    binding="imported_binding",
                    hops=2,
                ),
                _origin_hop(
                    0,
                    0,
                    0,
                    module_path="b.pietto",
                    exported_name="Row",
                    facade_origin="explicit_reexport",
                    target_module_path="c.pietto",
                ),
                _origin_hop(0, 0, 1, module_path="c.pietto", exported_name="Row"),
            ),
        ),
        "availability_states": (
            DifferentialPurpose.AVAILABILITY_STATES,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                *(
                    _declaration(
                        0,
                        position,
                        owner_name="a.pietto",
                        declared_name=name,
                        namespace=namespace,
                        declaration_kind=(
                            "table" if namespace == "relation" else "shape"
                        ),
                        availability=availability,
                        occurrence_count=count,
                        occurrence_index=index,
                        relation_status=status,
                        relation_reason=reason,
                    )
                    for position, (
                        name,
                        namespace,
                        availability,
                        count,
                        index,
                        status,
                        reason,
                    ) in enumerate(_AVAILABILITY_STATE_ROWS)
                ),
            ),
        ),
        "module_cycle_and_blocked_readiness": (
            DifferentialPurpose.MODULE_CYCLE_AND_BLOCKED_READINESS,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(
                    0, status="blocked", reason="module_cycle_blocked", cycles=1
                ),
                _cycle(0, 0, 2),
                _cycle_member(0, 0, 0, "a.pietto"),
                _cycle_member(0, 0, 1, "b.pietto"),
                _graph(0, cyclic=True, members=2, targets=1, evidence=1),
                _component_member(0, 0, "a.pietto"),
                _component_member(0, 1, "b.pietto"),
                _dependency_target(0, 0, "b.pietto"),
                _import_evidence(0, 0, "b.pietto"),
            ),
        ),
        "duplicate_nominal_identity_bucket": (
            DifferentialPurpose.DUPLICATE_NOMINAL_IDENTITY_BUCKET,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="Row",
                    availability="ambiguous",
                    occurrence_count=2,
                    occurrence_index=0,
                ),
                _declaration(
                    0,
                    1,
                    owner_name="a.pietto",
                    declared_name="Row",
                    availability="ambiguous",
                    occurrence_count=2,
                    occurrence_index=1,
                ),
            ),
        ),
        "equal_digest_distinct_modules": (
            DifferentialPurpose.EQUAL_DIGEST_DISTINCT_MODULES,
            _document(
                _header(2),
                _OWNER,
                *_module_block(0, "a.pietto", digest=_DIGEST_A),
                *_module_block(1, "b.pietto", digest=_DIGEST_A),
            ),
        ),
        "direct_and_renamed_lineage": (
            DifferentialPurpose.DIRECT_AND_RENAMED_LINEAGE,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _row_lineage(0, 0, fields=2),
                _lineage_field(0, 0, 0, name="id", field_position=0, paths=1),
                _lineage_path(
                    0,
                    0,
                    0,
                    0,
                    root_module_path="b.pietto",
                    root_field_name="id",
                    hops=1,
                ),
                _lineage_hop(
                    0,
                    0,
                    0,
                    0,
                    0,
                    projection_kind="direct",
                    output_field_name="id",
                    upstream_field_name="id",
                ),
                _lineage_field(0, 0, 1, name="total", field_position=1, paths=1),
                _lineage_path(
                    0,
                    0,
                    1,
                    0,
                    root_module_path="b.pietto",
                    root_field_name="amount",
                    root_field_position=1,
                    hops=1,
                ),
                _lineage_hop(
                    0,
                    0,
                    1,
                    0,
                    0,
                    projection_kind="renamed",
                    output_field_name="total",
                    upstream_field_name="amount",
                ),
            ),
        ),
        "preserved_semantic_facts": (
            DifferentialPurpose.PRESERVED_SEMANTIC_FACTS,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _semantic_facts(
                    0,
                    0,
                    let_bindings=1,
                    selects=2,
                    clause_dependencies=2,
                    window_outputs=2,
                ),
                _let_binding(0, 0, 0, binding_ordinal=0, has_value_type=True),
                _select(0, 0, 0, selected_output_ordinal=0, output_name="id"),
                _select(0, 0, 1, selected_output_ordinal=1, output_name=None),
                _clause_dependency(
                    0,
                    0,
                    0,
                    role="group_key",
                    source_ordinal=0,
                    status="concrete",
                ),
                _clause_dependency(
                    0,
                    0,
                    1,
                    role="grouped_order",
                    source_ordinal=0,
                    status="ambiguous",
                ),
                _window_output(
                    0,
                    0,
                    0,
                    selected_output_ordinal=1,
                    output_name="rank",
                    status="deferred",
                ),
                _window_output(
                    0,
                    0,
                    1,
                    selected_output_ordinal=2,
                    output_name=None,
                    status="unknown",
                ),
            ),
        ),
        "nullability_and_result_role": (
            DifferentialPurpose.NULLABILITY_AND_RESULT_ROLE,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="result",
                    namespace="relation",
                    declaration_kind="query",
                    availability="concrete",
                    relation_status="concrete",
                    relation_reason="direct_source_concrete",
                    row_fields=4,
                ),
                _row_field(0, 0, 0, name="id", nullability="non_null"),
                _row_field(
                    0,
                    0,
                    1,
                    name="category",
                    nullability="nullable",
                    result_role="group_key",
                ),
                _row_field(
                    0,
                    0,
                    2,
                    name="total",
                    nullability="unknown",
                    result_role="aggregate_result",
                ),
                _row_field(
                    0,
                    0,
                    3,
                    name="rank",
                    nullability="non_null",
                    result_role="window_result",
                ),
            ),
        ),
        "surrogate_text": (
            DifferentialPurpose.SURROGATE_TEXT,
            _document(_header(1), _OWNER, *_module_block(0, _SURROGATE_PATH)),
        ),
        "control_character_text": (
            DifferentialPurpose.CONTROL_CHARACTER_TEXT,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _declaration(0, 0, owner_name="a.pietto", declared_name=_CONTROL_TEXT),
            ),
        ),
        "non_ascii_text": (
            DifferentialPurpose.NON_ASCII_TEXT,
            _document(_header(1), _OWNER, *_module_block(0, _NON_ASCII_PATH)),
        ),
        "absent_versus_empty_text": (
            DifferentialPurpose.ABSENT_VERSUS_EMPTY_TEXT,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _export(0, 0, local_name="Row", module_path="a.pietto"),
                _export(
                    0,
                    1,
                    local_name="Missing",
                    module_path="a.pietto",
                    entry_origin=None,
                    item=1,
                    issues=1,
                ),
                _export_issue(0, 1, 0, "unresolved_export_binding"),
                _issue(0, 0, family="graph", status="module_import_cycle"),
                _issue(
                    0,
                    1,
                    family="relation",
                    status="unknown_relation_reference",
                    local_name="",
                ),
            ),
        ),
        "boundary_cardinalities": (
            DifferentialPurpose.BOUNDARY_CARDINALITIES,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(
                    0, status="blocked", reason="module_cycle_blocked", cycles=3
                ),
                *(
                    record
                    for cycle in range(3)
                    for record in (
                        _cycle(0, cycle, 3),
                        _cycle_member(0, cycle, 0, "a.pietto"),
                        _cycle_member(0, cycle, 1, "b.pietto"),
                        _cycle_member(0, cycle, 2, "c.pietto"),
                    )
                ),
                _graph(0, cyclic=True, members=3, targets=0, evidence=0),
                _component_member(0, 0, "a.pietto"),
                _component_member(0, 1, "b.pietto"),
                _component_member(0, 2, "c.pietto"),
            ),
        ),
        "large_repeated_bucket": (
            DifferentialPurpose.LARGE_REPEATED_BUCKET,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                *(
                    _declaration(
                        0,
                        position,
                        owner_name="a.pietto",
                        declared_name="Row",
                        availability="ambiguous",
                        occurrence_count=6,
                        occurrence_index=position,
                    )
                    for position in range(6)
                ),
            ),
        ),
        "issue_families": (
            DifferentialPurpose.ISSUE_FAMILIES,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _issue(0, 0, family="graph", status="unresolved_target_module"),
                _issue(
                    0,
                    1,
                    family="type_source",
                    status="ambiguous_local_type_name",
                    local_name="Row",
                ),
                _issue(
                    0,
                    2,
                    family="relation",
                    status="local_relation_cycle",
                    local_name="rows",
                ),
            ),
        ),
        "type_alias_chain": (
            DifferentialPurpose.TYPE_ALIAS_CHAIN,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _type_resolution(
                    0,
                    0,
                    canonical_name="Int",
                    canonical_kind="builtin",
                    direct_kind="type",
                    alias_chain=2,
                ),
                _type_alias(0, 0, 0, module_path="a.pietto", declared_name="Years"),
                _type_alias(0, 0, 1, module_path="b.pietto", declared_name="Age"),
                _type_resolution(
                    0,
                    1,
                    canonical_name="Text",
                    member_position=1,
                ),
            ),
        ),
        "issue_buckets": (
            DifferentialPurpose.ISSUE_BUCKETS,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _import(
                    0,
                    0,
                    local_name="Row",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    resolved=False,
                    issues=2,
                ),
                _import_issue(0, 0, 0, "unresolved_target_module"),
                _import_issue(0, 0, 1, "duplicate_source_request"),
                _export(
                    0,
                    0,
                    local_name="Row",
                    module_path="a.pietto",
                    entry_origin=None,
                    issues=2,
                ),
                _export_issue(0, 0, 0, "ambiguous_local_declaration"),
                _export_issue(0, 0, 1, "ambiguous_candidate_set"),
            ),
        ),
        "dependency_target_variants": (
            DifferentialPurpose.DEPENDENCY_TARGET_VARIANTS,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _dependency(
                    0,
                    0,
                    kind="source_shape_reference",
                    reference_role="source_shape",
                    declaration_target=("b.pietto", 0, "Row"),
                ),
                _dependency(
                    0,
                    1,
                    kind="row_field_reference",
                    reference_role="row_field",
                    member_position=1,
                    row_field_target=(1, "source_field", 0, "id"),
                ),
                _dependency(
                    0,
                    2,
                    kind="relation_reference",
                    reference_role="relation_from",
                    member_position=2,
                    declaration_target=("b.pietto", 1, "rows"),
                ),
            ),
        ),
        "boolean_values": (
            DifferentialPurpose.BOOLEAN_VALUES,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, cyclic=True, members=1, targets=1, evidence=1),
                _component_member(0, 0, "a.pietto"),
                _dependency_target(0, 0, "a.pietto"),
                _import_evidence(0, 0, "a.pietto"),
                _semantic_facts(0, 0, let_bindings=2),
                _let_binding(0, 0, 0, binding_ordinal=0, has_value_type=True),
                _let_binding(0, 0, 1, binding_ordinal=1, has_value_type=False),
            ),
        ),
        "resolution_sections": (
            DifferentialPurpose.RESOLUTION_SECTIONS,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _type_resolution(0, 0, canonical_name="Int"),
                _source_shape_resolution(
                    0,
                    0,
                    owner_position=1,
                    target_module_path="b.pietto",
                    target_declared_name="Row",
                ),
                _source_shape_resolution(
                    0,
                    1,
                    owner_position=2,
                    target_module_path="b.pietto",
                    target_declared_name="Row",
                ),
                _relation_resolution(
                    0,
                    0,
                    owner_position=3,
                    local_name="rows",
                    target_module_path="b.pietto",
                    target_declared_name="rows",
                ),
                _relation_resolution(
                    0,
                    1,
                    owner_position=4,
                    local_name="r",
                    target_module_path="b.pietto",
                    target_declared_name="rows",
                ),
            ),
        ),
        "unresolved_import": (
            DifferentialPurpose.UNRESOLVED_IMPORT,
            _document(
                _header(1),
                _OWNER,
                *_module_block(0, "a.pietto"),
                _import(
                    0,
                    0,
                    local_name="Row",
                    exported_name="Row",
                    target_module_path="missing.pietto",
                    resolved=False,
                    issues=1,
                ),
                _import_issue(0, 0, 0, "unresolved_target_module"),
            ),
        ),
    }


def _rejected_vectors() -> tuple[DifferentialVector, ...]:
    """Return every portable rejection vector with its exact expectation."""

    valid_module = _module_block(0, "a.pietto")
    return (
        _rejected(
            "empty_document",
            DifferentialPurpose.EMPTY_DOCUMENT,
            _document(),
            ProjectPureStatus.EMPTY_DOCUMENT,
        ),
        _rejected(
            "missing_inspection_header",
            DifferentialPurpose.MISSING_HEADER,
            _document(_OWNER, _header(0)),
            ProjectPureStatus.MISSING_HEADER_RECORD,
            0,
        ),
        _rejected(
            "absent_owner_header_record",
            DifferentialPurpose.ABSENT_HEADER_RECORD,
            _document(_header(0)),
            ProjectPureStatus.MISSING_HEADER_RECORD,
        ),
        _rejected(
            "missing_owner_header",
            DifferentialPurpose.MISSING_HEADER,
            _document(_header(1), *valid_module),
            ProjectPureStatus.MISSING_HEADER_RECORD,
            1,
        ),
        _rejected(
            "duplicate_inspection_header",
            DifferentialPurpose.UNEXPECTED_HEADER,
            _document(_header(1), _OWNER, _header(1), *valid_module),
            ProjectPureStatus.UNEXPECTED_HEADER_RECORD,
            2,
        ),
        _rejected(
            "duplicate_owner_header",
            DifferentialPurpose.UNEXPECTED_HEADER,
            _document(_header(1), _OWNER, _OWNER, *valid_module),
            ProjectPureStatus.UNEXPECTED_HEADER_RECORD,
            2,
        ),
        _rejected(
            "trailing_record_after_empty_document",
            DifferentialPurpose.TRAILING_RECORD,
            _document(_header(0), _OWNER, *valid_module),
            ProjectPureStatus.TRAILING_RECORD_AFTER_DOCUMENT,
            2,
        ),
        _rejected(
            "wrong_format_marker",
            DifferentialPurpose.WRONG_FORMAT_MARKER,
            _document(_header(0, "pietto.module-inspection.v2"), _OWNER),
            ProjectPureStatus.UNKNOWN_FORMAT_MARKER,
            0,
            0,
        ),
        _rejected(
            "stale_format_marker",
            DifferentialPurpose.STALE_FORMAT_MARKER,
            _document(_header(0, "pietto.module-inspection.v0"), _OWNER),
            ProjectPureStatus.UNKNOWN_FORMAT_MARKER,
            0,
            0,
        ),
        _rejected(
            "unknown_record_kind",
            DifferentialPurpose.UNKNOWN_RECORD_KIND,
            _document(
                _header(1),
                _OWNER,
                _record("module_manifest", ("module", pure_integer(0))),
                *valid_module,
            ),
            ProjectPureStatus.UNKNOWN_RECORD_KIND,
            2,
        ),
        _rejected(
            "unknown_key",
            DifferentialPurpose.UNKNOWN_KEY,
            _document(
                _header(1),
                _OWNER,
                _record(
                    "module",
                    ("module", pure_integer(0)),
                    ("location", pure_text("a.pietto")),
                ),
            ),
            ProjectPureStatus.FIELD_KEY_MISMATCH,
            2,
            1,
        ),
        _rejected(
            "missing_key",
            DifferentialPurpose.MISSING_KEY,
            _document(
                _header(1), _OWNER, _record("module", ("module", pure_integer(0)))
            ),
            ProjectPureStatus.FIELD_ARITY_MISMATCH,
            2,
        ),
        _rejected(
            "extra_key",
            DifferentialPurpose.EXTRA_KEY,
            _document(
                _header(1),
                _OWNER,
                _record(
                    "module",
                    ("module", pure_integer(0)),
                    ("path", pure_text("a.pietto")),
                    ("extra", pure_text("x")),
                ),
            ),
            ProjectPureStatus.FIELD_ARITY_MISMATCH,
            2,
        ),
        _rejected(
            "wrong_key_order",
            DifferentialPurpose.WRONG_KEY_ORDER,
            _document(
                _header(1),
                _OWNER,
                _record(
                    "module",
                    ("path", pure_text("a.pietto")),
                    ("module", pure_integer(0)),
                ),
            ),
            ProjectPureStatus.FIELD_KEY_MISMATCH,
            2,
            0,
        ),
        _rejected(
            "wrong_value_tag",
            DifferentialPurpose.WRONG_VALUE_TAG,
            _document(
                _header(1),
                _OWNER,
                _record(
                    "module",
                    ("module", pure_integer(0)),
                    ("path", pure_integer(7)),
                ),
            ),
            ProjectPureStatus.VALUE_TAG_MISMATCH,
            2,
            1,
        ),
        _rejected(
            "absent_not_allowed",
            DifferentialPurpose.ABSENT_NOT_ALLOWED,
            _document(
                _header(1),
                _OWNER,
                _record("module", ("module", pure_integer(0)), ("path", PURE_ABSENT)),
            ),
            ProjectPureStatus.ABSENT_VALUE_NOT_ALLOWED,
            2,
            1,
        ),
        _rejected(
            "missing_payload",
            DifferentialPurpose.MISSING_PAYLOAD,
            _document(
                _header(1),
                _OWNER,
                _record(
                    "module",
                    ("module", pure_integer(0)),
                    ("path", ProjectPureValue(tag=ProjectPureTag.TEXT)),
                ),
            ),
            ProjectPureStatus.MISSING_VALUE_PAYLOAD,
            2,
            1,
        ),
        _rejected(
            "extra_payload",
            DifferentialPurpose.EXTRA_PAYLOAD,
            _document(
                _header(1),
                _OWNER,
                _record(
                    "module",
                    ("module", pure_integer(0)),
                    (
                        "path",
                        ProjectPureValue(
                            tag=ProjectPureTag.TEXT, text="a.pietto", integer=3
                        ),
                    ),
                ),
            ),
            ProjectPureStatus.EXTRA_VALUE_PAYLOAD,
            2,
            1,
        ),
        _rejected(
            "negative_integer",
            DifferentialPurpose.NEGATIVE_INTEGER,
            _document(
                _record(
                    "inspection",
                    ("format", pure_enumeration(PURE_DOCUMENT_FORMAT_MARKER)),
                    ("modules", pure_integer(-1)),
                ),
                _OWNER,
            ),
            ProjectPureStatus.NEGATIVE_INTEGER,
            0,
            1,
        ),
        _rejected(
            "unknown_enumeration",
            DifferentialPurpose.UNKNOWN_ENUMERATION,
            _document(
                _header(0),
                _record(
                    "owner",
                    ("kind", pure_enumeration("remote_registry_root")),
                    ("namespace", pure_text("")),
                    ("name", pure_text("")),
                ),
            ),
            ProjectPureStatus.UNKNOWN_ENUMERATION,
            1,
            0,
        ),
        _rejected(
            "orphan_module_scoped_record",
            DifferentialPurpose.ORPHAN_RECORD,
            _document(_header(1), _OWNER, _digest(0), *valid_module),
            ProjectPureStatus.ORPHAN_RECORD,
            2,
        ),
        _rejected(
            "wrong_parent_ordinal",
            DifferentialPurpose.WRONG_PARENT_ORDINAL,
            _document(_header(1), _OWNER, _module(0, "a.pietto"), _digest(1)),
            ProjectPureStatus.SCOPE_ORDINAL_MISMATCH,
            3,
        ),
        _rejected(
            "reordered_sections",
            DifferentialPurpose.REORDERED_SECTIONS,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _graph(0),
                _component_member(0, 0, "a.pietto"),
                _readiness(0),
            ),
            ProjectPureStatus.SECTION_ORDER_VIOLATION,
            6,
        ),
        _rejected(
            "reordered_sibling_kinds",
            DifferentialPurpose.REORDERED_SIBLING_KINDS,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, members=1, targets=1),
                _dependency_target(0, 0, "b.pietto"),
                _component_member(0, 0, "a.pietto"),
            ),
            ProjectPureStatus.CHILD_ORDER_VIOLATION,
            7,
        ),
        _rejected(
            "duplicated_record",
            DifferentialPurpose.DUPLICATED_RECORD,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, cyclic=True, members=2),
                _component_member(0, 0, "a.pietto"),
                _component_member(0, 0, "a.pietto"),
            ),
            ProjectPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            7,
        ),
        _rejected(
            "missing_record",
            DifferentialPurpose.MISSING_RECORD,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, cyclic=True, members=2),
                _component_member(0, 0, "a.pietto"),
            ),
            ProjectPureStatus.CHILD_COUNT_MISMATCH,
            5,
        ),
        _rejected(
            "non_dense_ordinal",
            DifferentialPurpose.NON_DENSE_ORDINAL,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, members=1),
                _component_member(0, 1, "a.pietto"),
            ),
            ProjectPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            6,
        ),
        _rejected(
            "non_dense_declaration_ordinal",
            DifferentialPurpose.NON_DENSE_DECLARATION_ORDINAL,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(0, 0, owner_name="a.pietto", declared_name="First"),
                _declaration(0, 2, owner_name="a.pietto", declared_name="Second"),
            ),
            ProjectPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            8,
        ),
        _rejected(
            "child_count_too_large",
            DifferentialPurpose.CHILD_COUNT_TOO_LARGE,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, members=1, targets=0),
                _component_member(0, 0, "a.pietto"),
                _dependency_target(0, 0, "b.pietto"),
            ),
            ProjectPureStatus.CHILD_COUNT_MISMATCH,
            5,
        ),
        _rejected(
            "inconsistent_readiness_state",
            DifferentialPurpose.INCONSISTENT_READINESS_STATE,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0, status="ready", reason="module_cycle_blocked"),
                _graph(0),
                _component_member(0, 0, "a.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            4,
        ),
        _rejected(
            "integer_out_of_range",
            DifferentialPurpose.INTEGER_OUT_OF_RANGE,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0, byte_count=PURE_MAX_INTEGER + 1),
            ),
            ProjectPureStatus.INTEGER_OUT_OF_RANGE,
            3,
            3,
        ),
        _rejected(
            "partial_presence_group",
            DifferentialPurpose.PARTIAL_PRESENCE_GROUP,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _record(
                    "export",
                    ("module", pure_integer(0)),
                    ("request", pure_integer(0)),
                    ("local_name", pure_text("Row")),
                    ("namespace", pure_enumeration("type")),
                    ("declaration_kind", pure_enumeration("shape")),
                    ("module_statement_position", pure_integer(0)),
                    ("item_position", pure_integer(0)),
                    ("exposed_name", pure_text("Row")),
                    ("entry_origin", PURE_ABSENT),
                    ("target_module_path", PURE_ABSENT),
                    ("target_namespace", PURE_ABSENT),
                    ("target_declaration_kind", PURE_ABSENT),
                    ("target_declared_name", PURE_ABSENT),
                    ("issues", pure_integer(0)),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "dependency_without_a_target",
            DifferentialPurpose.DEPENDENCY_WITHOUT_A_TARGET,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _dependency(
                    0,
                    0,
                    kind="relation_reference",
                    reference_role="relation_from",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "dependency_kind_target_mismatch",
            DifferentialPurpose.DEPENDENCY_KIND_TARGET_MISMATCH,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _dependency(
                    0,
                    0,
                    kind="row_field_reference",
                    reference_role="row_field",
                    declaration_target=("b.pietto", 0, "Row"),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "canonical_kind_target_mismatch",
            DifferentialPurpose.CANONICAL_KIND_TARGET_MISMATCH,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _type_resolution(
                    0,
                    0,
                    canonical_name="Int",
                    canonical_kind="builtin",
                    canonical_target=("b.pietto", "Age"),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "issue_status_outside_its_family",
            DifferentialPurpose.ISSUE_STATUS_OUTSIDE_ITS_FAMILY,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _issue(0, 0, family="graph", status="unknown_relation_reference"),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "non_concrete_lineage_with_fields",
            DifferentialPurpose.NON_CONCRETE_LINEAGE_WITH_FIELDS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _row_lineage(0, 0, status="unknown", reason="unknown_schema", fields=1),
                _lineage_field(0, 0, 0, name="id", paths=0),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "imported_origin_without_hops",
            DifferentialPurpose.IMPORTED_ORIGIN_WITHOUT_HOPS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _origin(
                    0,
                    0,
                    local_name="Row",
                    target_module_path="b.pietto",
                    target_declared_name="Row",
                    binding="imported_binding",
                    hops=0,
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "lineage_field_without_paths",
            DifferentialPurpose.LINEAGE_FIELD_WITHOUT_PATHS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _row_lineage(0, 0, fields=1),
                _lineage_field(0, 0, 0, name="id", paths=0),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "digest_not_lowercase_hex",
            DifferentialPurpose.DIGEST_NOT_LOWERCASE_HEX,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0, digest="Z" * 64),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            3,
        ),
        _rejected(
            "named_project_root_owner",
            DifferentialPurpose.NAMED_PROJECT_ROOT_OWNER,
            _document(
                _header(0),
                _record(
                    "owner",
                    ("kind", pure_enumeration("local_project_root")),
                    ("namespace", pure_text("")),
                    ("name", pure_text("pietto")),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            1,
        ),
        _rejected(
            "availability_relation_state_mismatch",
            DifferentialPurpose.AVAILABILITY_RELATION_STATE_MISMATCH,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="rows",
                    namespace="relation",
                    declaration_kind="source",
                    availability="unknown",
                    relation_status="concrete",
                    relation_reason="direct_source_concrete",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "ineligible_namespace_kind_pair",
            DifferentialPurpose.INELIGIBLE_NAMESPACE_KIND_PAIR,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _import(
                    0,
                    0,
                    local_name="Row",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    namespace="callable",
                    declaration_kind="shape",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "multi_member_acyclic_component",
            DifferentialPurpose.MULTI_MEMBER_ACYCLIC_COMPONENT,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, cyclic=False, members=2),
                _component_member(0, 0, "a.pietto"),
                _component_member(0, 1, "b.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            5,
        ),
        _rejected(
            "unterminated_origin_hop_chain",
            DifferentialPurpose.UNTERMINATED_ORIGIN_HOP_CHAIN,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _origin(
                    0,
                    0,
                    local_name="Row",
                    target_module_path="b.pietto",
                    target_declared_name="Row",
                    binding="imported_binding",
                    hops=1,
                ),
                _origin_hop(
                    0,
                    0,
                    0,
                    module_path="b.pietto",
                    exported_name="Row",
                    facade_origin="explicit_reexport",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "canonical_kind_name_mismatch",
            DifferentialPurpose.CANONICAL_KIND_NAME_MISMATCH,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _type_resolution(0, 0, canonical_name="NotABuiltin"),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "alias_identity_not_a_type_alias",
            DifferentialPurpose.ALIAS_IDENTITY_NOT_A_TYPE_ALIAS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _type_resolution(
                    0, 0, canonical_name="Int", direct_kind="type", alias_chain=1
                ),
                _record(
                    "type_resolution_alias",
                    ("module", pure_integer(0)),
                    ("resolution", pure_integer(0)),
                    ("alias", pure_integer(0)),
                    ("module_path", pure_text("a.pietto")),
                    ("namespace", pure_enumeration("relation")),
                    ("declaration_kind", pure_enumeration("query")),
                    ("declared_name", pure_text("Years")),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "empty_select_output_name",
            DifferentialPurpose.EMPTY_SELECT_OUTPUT_NAME,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, selects=1),
                _select(0, 0, 0, selected_output_ordinal=0, output_name=""),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "non_relation_relation_availability",
            DifferentialPurpose.NON_RELATION_RELATION_AVAILABILITY,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="Row",
                    availability="concrete",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "ambiguous_without_repetition",
            DifferentialPurpose.AMBIGUOUS_WITHOUT_REPETITION,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="Row",
                    availability="ambiguous",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "hop_endpoints_disagree",
            DifferentialPurpose.HOP_ENDPOINTS_DISAGREE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _origin(
                    0,
                    0,
                    local_name="Row",
                    target_module_path="b.pietto",
                    target_declared_name="Row",
                    binding="imported_binding",
                    hops=1,
                ),
                _record(
                    "origin_hop",
                    ("module", pure_integer(0)),
                    ("origin", pure_integer(0)),
                    ("hop", pure_integer(0)),
                    ("import_target_module_path", pure_text("b.pietto")),
                    ("import_exported_name", pure_text("Row")),
                    ("import_module_statement_position", pure_integer(0)),
                    ("import_item_position", pure_integer(0)),
                    ("facade_module_path", pure_text("c.pietto")),
                    ("facade_exposed_name", pure_text("Row")),
                    ("facade_origin", pure_enumeration("local_declaration")),
                    ("target_module_path", pure_text("b.pietto")),
                    ("target_declared_name", pure_text("Row")),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "acyclic_component_with_self_edge",
            DifferentialPurpose.ACYCLIC_COMPONENT_WITH_SELF_EDGE,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, members=1, targets=1, evidence=1),
                _component_member(0, 0, "a.pietto"),
                _dependency_target(0, 0, "a.pietto"),
                _import_evidence(0, 0, "a.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            5,
        ),
        _rejected(
            "rewritten_select_ordinal",
            DifferentialPurpose.REWRITTEN_SELECT_ORDINAL,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, selects=1),
                _select(0, 0, 0, selected_output_ordinal=99, output_name="id"),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "sparse_clause_source_ledger",
            DifferentialPurpose.SPARSE_CLAUSE_SOURCE_LEDGER,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, clause_dependencies=1),
                _clause_dependency(
                    0,
                    0,
                    0,
                    role="group_key",
                    source_ordinal=99,
                    status="concrete",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
        ),
        _rejected(
            "unordered_clause_roles",
            DifferentialPurpose.UNORDERED_CLAUSE_ROLES,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, clause_dependencies=2),
                _clause_dependency(
                    0,
                    0,
                    0,
                    role="grouped_order",
                    source_ordinal=0,
                    status="concrete",
                ),
                _clause_dependency(
                    0,
                    0,
                    1,
                    role="group_key",
                    source_ordinal=0,
                    status="concrete",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            9,
        ),
        _rejected(
            "unordered_window_outputs",
            DifferentialPurpose.UNORDERED_WINDOW_OUTPUTS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, window_outputs=2),
                _window_output(
                    0,
                    0,
                    0,
                    selected_output_ordinal=2,
                    output_name="rank",
                    status="concrete",
                ),
                _window_output(
                    0,
                    0,
                    1,
                    selected_output_ordinal=1,
                    output_name="dense",
                    status="concrete",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            9,
        ),
        _rejected(
            "self_cycle_without_self_edge",
            DifferentialPurpose.SELF_CYCLE_WITHOUT_SELF_EDGE,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, cyclic=True, members=1, targets=1, evidence=1),
                _component_member(0, 0, "a.pietto"),
                _dependency_target(0, 0, "b.pietto"),
                _import_evidence(0, 0, "b.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            5,
        ),
        _rejected(
            "unordered_import_evidence",
            DifferentialPurpose.UNORDERED_IMPORT_EVIDENCE,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, targets=1, evidence=2),
                _component_member(0, 0, "a.pietto"),
                _dependency_target(0, 0, "b.pietto"),
                _import_evidence(0, 0, "b.pietto", statement=1, item=0),
                _import_evidence(0, 1, "b.pietto", statement=0, item=1),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            9,
        ),
        _rejected(
            "empty_window_output_name",
            DifferentialPurpose.EMPTY_WINDOW_OUTPUT_NAME,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, window_outputs=1),
                _window_output(
                    0,
                    0,
                    0,
                    selected_output_ordinal=0,
                    output_name="",
                    status="concrete",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "rewritten_let_binding_ordinal",
            DifferentialPurpose.REWRITTEN_LET_BINDING_ORDINAL,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, let_bindings=1),
                _let_binding(0, 0, 0, binding_ordinal=99, has_value_type=True),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "module_path_outside_its_domain",
            DifferentialPurpose.MODULE_PATH_OUTSIDE_ITS_DOMAIN,
            _document(_header(1), _OWNER, *_module_block(0, "../a.pietto")),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            2,
        ),
        _rejected(
            "declaration_namespace_kind_pair",
            DifferentialPurpose.DECLARATION_NAMESPACE_KIND_PAIR,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="Row",
                    namespace="relation",
                    declaration_kind="type",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "repeated_lineage_owner",
            DifferentialPurpose.REPEATED_LINEAGE_OWNER,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _row_lineage(0, 0, owner_position=0),
                _row_lineage(0, 1, owner_position=0),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            8,
        ),
        _rejected(
            "shape_field_in_relation_lineage",
            DifferentialPurpose.SHAPE_FIELD_IN_RELATION_LINEAGE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _row_lineage(0, 0, fields=1),
                _lineage_field(0, 0, 0, name="id", kind="shape_field", paths=1),
                _lineage_path(
                    0,
                    0,
                    0,
                    0,
                    root_module_path="a.pietto",
                    root_field_name="id",
                ),
            ),
            ProjectPureStatus.UNKNOWN_ENUMERATION,
            8,
            3,
        ),
        _rejected(
            "duplicate_module_path",
            DifferentialPurpose.DUPLICATE_MODULE_PATH,
            _document(
                _header(2),
                _OWNER,
                *_module_block(0, "a.pietto"),
                *_module_block(1, "a.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
        ),
        _rejected(
            "evidence_outside_dependency_targets",
            DifferentialPurpose.EVIDENCE_OUTSIDE_DEPENDENCY_TARGETS,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0, targets=1, evidence=1),
                _component_member(0, 0, "a.pietto"),
                _dependency_target(0, 0, "b.pietto"),
                _import_evidence(0, 0, "c.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            5,
        ),
        _rejected(
            "unresolved_import_without_blocking_issue",
            DifferentialPurpose.UNRESOLVED_IMPORT_WITHOUT_BLOCKING_ISSUE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _import(
                    0,
                    0,
                    local_name="Row",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    resolved=False,
                    issues=1,
                ),
                _import_issue(0, 0, 0, "duplicate_source_request"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
        ),
        _rejected(
            "unentered_export_without_blocking_issue",
            DifferentialPurpose.UNENTERED_EXPORT_WITHOUT_BLOCKING_ISSUE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _export(
                    0,
                    0,
                    local_name="Row",
                    module_path="a.pietto",
                    entry_origin=None,
                    issues=1,
                ),
                _export_issue(0, 0, 0, "duplicate_source_request"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
        ),
        _rejected(
            "incomplete_occurrence_bucket",
            DifferentialPurpose.INCOMPLETE_OCCURRENCE_BUCKET,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="Row",
                    availability="ambiguous",
                    occurrence_count=2,
                    occurrence_index=0,
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            2,
        ),
        _rejected(
            "cycle_disagrees_with_component",
            DifferentialPurpose.CYCLE_DISAGREES_WITH_COMPONENT,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(
                    0, status="blocked", reason="module_cycle_blocked", cycles=1
                ),
                _cycle(0, 0, 2),
                _cycle_member(0, 0, 0, "a.pietto"),
                _cycle_member(0, 0, 1, "foreign.pietto"),
                _graph(0, cyclic=True, members=2, targets=0, evidence=0),
                _component_member(0, 0, "a.pietto"),
                _component_member(0, 1, "b.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            2,
        ),
        _rejected(
            "dependency_role_kind_mismatch",
            DifferentialPurpose.DEPENDENCY_ROLE_KIND_MISMATCH,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _dependency(
                    0,
                    0,
                    kind="source_shape_reference",
                    reference_role="row_field",
                    declaration_target=("b.pietto", 0, "Row"),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "repeated_lineage_field_position",
            DifferentialPurpose.REPEATED_LINEAGE_FIELD_POSITION,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _row_lineage(0, 0, fields=2),
                _lineage_field(0, 0, 0, name="id", field_position=0, paths=1),
                _lineage_path(
                    0,
                    0,
                    0,
                    0,
                    root_module_path="a.pietto",
                    root_field_name="id",
                ),
                _lineage_field(0, 0, 1, name="total", field_position=0, paths=1),
                _lineage_path(
                    0,
                    0,
                    1,
                    0,
                    root_module_path="a.pietto",
                    root_field_name="total",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            10,
        ),
        _rejected(
            "unordered_import_positions",
            DifferentialPurpose.UNORDERED_IMPORT_POSITIONS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _import(
                    0,
                    0,
                    local_name="First",
                    exported_name="First",
                    target_module_path="b.pietto",
                    statement=1,
                    item=0,
                ),
                _import(
                    0,
                    1,
                    local_name="Second",
                    exported_name="Second",
                    target_module_path="b.pietto",
                    statement=0,
                    item=1,
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            8,
        ),
        _rejected(
            "resolved_import_with_blocking_issue",
            DifferentialPurpose.RESOLVED_IMPORT_WITH_BLOCKING_ISSUE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _import(
                    0,
                    0,
                    local_name="Row",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    issues=1,
                ),
                _import_issue(0, 0, 0, "unresolved_target_module"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            8,
        ),
        _rejected(
            "resolved_export_with_blocking_issue",
            DifferentialPurpose.RESOLVED_EXPORT_WITH_BLOCKING_ISSUE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _export(
                    0,
                    0,
                    local_name="Row",
                    module_path="a.pietto",
                    issues=1,
                ),
                _export_issue(0, 0, 0, "unresolved_export_binding"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            8,
        ),
        _rejected(
            "foreign_declaration_owner",
            DifferentialPurpose.FOREIGN_DECLARATION_OWNER,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(0, 0, owner_name="foreign.pietto", declared_name="Row"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
        ),
        _rejected(
            "foreign_local_export_target",
            DifferentialPurpose.FOREIGN_LOCAL_EXPORT_TARGET,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _export(
                    0,
                    0,
                    local_name="Row",
                    module_path="foreign.pietto",
                    entry_origin="local_declaration",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
        ),
        _rejected(
            "foreign_local_origin_target",
            DifferentialPurpose.FOREIGN_LOCAL_ORIGIN_TARGET,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _origin(
                    0,
                    0,
                    local_name="Row",
                    target_module_path="foreign.pietto",
                    target_declared_name="Row",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
        ),
        _rejected(
            "hop_target_outside_its_origin",
            DifferentialPurpose.HOP_TARGET_OUTSIDE_ITS_ORIGIN,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _origin(
                    0,
                    0,
                    local_name="Row",
                    target_module_path="c.pietto",
                    target_declared_name="Row",
                    binding="imported_binding",
                    hops=2,
                ),
                _origin_hop(
                    0,
                    0,
                    0,
                    module_path="b.pietto",
                    exported_name="Row",
                    facade_origin="explicit_reexport",
                ),
                _origin_hop(0, 0, 1, module_path="c.pietto", exported_name="Row"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            8,
        ),
        _rejected(
            "lineage_chain_wrong_endpoint",
            DifferentialPurpose.LINEAGE_CHAIN_WRONG_ENDPOINT,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _row_lineage(0, 0, fields=1),
                _lineage_field(0, 0, 0, name="id", paths=1),
                _lineage_path(
                    0,
                    0,
                    0,
                    0,
                    root_module_path="b.pietto",
                    root_field_name="id",
                    hops=1,
                ),
                _lineage_hop(
                    0,
                    0,
                    0,
                    0,
                    0,
                    projection_kind="direct",
                    output_field_name="other",
                    upstream_field_name="id",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            10,
        ),
        _rejected(
            "lineage_chain_not_contiguous",
            DifferentialPurpose.LINEAGE_CHAIN_NOT_CONTIGUOUS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _row_lineage(0, 0, fields=1),
                _lineage_field(0, 0, 0, name="id", paths=1),
                _lineage_path(
                    0,
                    0,
                    0,
                    0,
                    root_module_path="b.pietto",
                    root_field_name="root",
                    hops=2,
                ),
                _lineage_hop(
                    0,
                    0,
                    0,
                    0,
                    0,
                    projection_kind="direct",
                    output_field_name="id",
                    upstream_field_name="middle",
                ),
                _lineage_hop(
                    0,
                    0,
                    0,
                    0,
                    1,
                    projection_kind="renamed",
                    output_field_name="other",
                    upstream_field_name="root",
                ),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            11,
        ),
        _rejected(
            "duplicate_alias_identity",
            DifferentialPurpose.DUPLICATE_ALIAS_IDENTITY,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _type_resolution(
                    0,
                    0,
                    direct_kind="type",
                    canonical_kind="shape",
                    canonical_name="Row",
                    canonical_target=("b.pietto", "Row"),
                    alias_chain=2,
                ),
                _type_alias(0, 0, 0, module_path="b.pietto", declared_name="Alias"),
                _type_alias(0, 0, 1, module_path="b.pietto", declared_name="Alias"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            9,
        ),
        _rejected(
            "component_without_its_module",
            DifferentialPurpose.COMPONENT_WITHOUT_ITS_MODULE,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(0),
                _graph(0),
                _component_member(0, 0, "foreign.pietto"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            5,
        ),
        _rejected(
            "duplicate_import_issue_status",
            DifferentialPurpose.DUPLICATE_IMPORT_ISSUE_STATUS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _import(
                    0,
                    0,
                    local_name="Row",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    resolved=False,
                    issues=2,
                ),
                _import_issue(0, 0, 0, "unresolved_target_module"),
                _import_issue(0, 0, 1, "unresolved_target_module"),
            ),
            ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
            9,
        ),
        _rejected(
            "earlier_scope_settles_first",
            DifferentialPurpose.EARLIER_SCOPE_SETTLES_FIRST,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(
                    0, status="blocked", reason="module_cycle_blocked", cycles=1
                ),
                _record(
                    "graph",
                    ("module", pure_integer(0)),
                    ("component_is_cyclic", pure_integer(0)),
                    ("component_members", pure_integer(1)),
                    ("dependency_targets", pure_integer(0)),
                    ("import_evidence", pure_integer(0)),
                ),
            ),
            ProjectPureStatus.CHILD_COUNT_MISMATCH,
            4,
        ),
        _rejected(
            "unresolved_import_without_issue",
            DifferentialPurpose.UNRESOLVED_IMPORT_WITHOUT_ISSUE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _import(
                    0,
                    0,
                    local_name="Row",
                    exported_name="Row",
                    target_module_path="b.pietto",
                    resolved=False,
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "unresolved_export_without_issue",
            DifferentialPurpose.UNRESOLVED_EXPORT_WITHOUT_ISSUE,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _export(
                    0,
                    0,
                    local_name="Row",
                    module_path="a.pietto",
                    entry_origin=None,
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "terminal_hop_target_disagrees",
            DifferentialPurpose.TERMINAL_HOP_TARGET_DISAGREES,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _origin(
                    0,
                    0,
                    local_name="Row",
                    target_module_path="b.pietto",
                    target_declared_name="Renamed",
                    binding="imported_binding",
                    hops=1,
                ),
                _record(
                    "origin_hop",
                    ("module", pure_integer(0)),
                    ("origin", pure_integer(0)),
                    ("hop", pure_integer(0)),
                    ("import_target_module_path", pure_text("b.pietto")),
                    ("import_exported_name", pure_text("Row")),
                    ("import_module_statement_position", pure_integer(0)),
                    ("import_item_position", pure_integer(0)),
                    ("facade_module_path", pure_text("b.pietto")),
                    ("facade_exposed_name", pure_text("Row")),
                    ("facade_origin", pure_enumeration("local_declaration")),
                    ("target_module_path", pure_text("b.pietto")),
                    ("target_declared_name", pure_text("Renamed")),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            8,
        ),
        _rejected(
            "clause_role_outside_subset",
            DifferentialPurpose.CLAUSE_ROLE_OUTSIDE_SUBSET,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, clause_dependencies=1),
                _clause_dependency(
                    0,
                    0,
                    0,
                    role="window_partition",
                    source_ordinal=0,
                    status="concrete",
                ),
            ),
            ProjectPureStatus.UNKNOWN_ENUMERATION,
            8,
            3,
        ),
        _rejected(
            "window_output_status_outside_subset",
            DifferentialPurpose.WINDOW_OUTPUT_STATUS_OUTSIDE_SUBSET,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _semantic_facts(0, 0, window_outputs=1),
                _window_output(
                    0,
                    0,
                    0,
                    selected_output_ordinal=0,
                    output_name="rank",
                    status="ambiguous",
                ),
            ),
            ProjectPureStatus.UNKNOWN_ENUMERATION,
            8,
            5,
        ),
        _rejected(
            "resolved_import_kind_mismatch",
            DifferentialPurpose.RESOLVED_IMPORT_KIND_MISMATCH,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _record(
                    "import",
                    ("module", pure_integer(0)),
                    ("request", pure_integer(0)),
                    ("local_name", pure_text("Row")),
                    ("namespace", pure_enumeration("type")),
                    ("declaration_kind", pure_enumeration("shape")),
                    ("target_module_path", pure_text("b.pietto")),
                    ("exported_name", pure_text("Row")),
                    ("module_statement_position", pure_integer(0)),
                    ("item_position", pure_integer(0)),
                    ("resolved_module_path", pure_text("b.pietto")),
                    ("resolved_namespace", pure_enumeration("relation")),
                    ("resolved_declaration_kind", pure_enumeration("query")),
                    ("resolved_declared_name", pure_text("Row")),
                    ("issues", pure_integer(0)),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "canonical_target_name_mismatch",
            DifferentialPurpose.CANONICAL_TARGET_NAME_MISMATCH,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _type_resolution(
                    0,
                    0,
                    canonical_name="Expected",
                    canonical_kind="shape",
                    canonical_target=("b.pietto", "Different"),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "exclusive_target_groups",
            DifferentialPurpose.EXCLUSIVE_TARGET_GROUPS,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _dependency(
                    0,
                    0,
                    kind="row_field_reference",
                    reference_role="row_field",
                    declaration_target=("b.pietto", 0, "Row"),
                    row_field_target=(1, "source_field", 0, "id"),
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "positive_requires_present",
            DifferentialPurpose.POSITIVE_REQUIRES_PRESENT,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="Row",
                    row_fields=1,
                ),
                _row_field(0, 0, 0, name="id"),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "occurrence_index_outside_bucket",
            DifferentialPurpose.OCCURRENCE_INDEX_OUTSIDE_BUCKET,
            _document(
                _header(1),
                _OWNER,
                *valid_module,
                _declaration(
                    0,
                    0,
                    owner_name="a.pietto",
                    declared_name="Row",
                    occurrence_count=1,
                    occurrence_index=1,
                ),
            ),
            ProjectPureStatus.INCONSISTENT_RECORD_STATE,
            7,
        ),
        _rejected(
            "missing_required_singleton",
            DifferentialPurpose.MISSING_REQUIRED_SINGLETON,
            _document(
                _header(1), _OWNER, _module(0, "a.pietto"), _digest(0), _readiness(0)
            ),
            ProjectPureStatus.MISSING_REQUIRED_RECORD,
            2,
        ),
        _rejected(
            "duplicate_singleton",
            DifferentialPurpose.DUPLICATE_SINGLETON,
            _document(
                _header(1), _OWNER, _module(0, "a.pietto"), _digest(0), _digest(0)
            ),
            ProjectPureStatus.DUPLICATE_SINGLETON_RECORD,
            4,
        ),
        _rejected(
            "module_count_mismatch",
            DifferentialPurpose.MODULE_COUNT_MISMATCH,
            _document(_header(2), _OWNER, *valid_module),
            ProjectPureStatus.CHILD_COUNT_MISMATCH,
            0,
        ),
        _rejected(
            "impossible_state_combination",
            DifferentialPurpose.IMPOSSIBLE_STATE_COMBINATION,
            _document(
                _header(1),
                _OWNER,
                _module(0, "a.pietto"),
                _digest(0),
                _readiness(
                    0, status="blocked", reason="module_cycle_blocked", cycles=1
                ),
                _graph(0),
                _component_member(0, 0, "a.pietto"),
            ),
            ProjectPureStatus.CHILD_COUNT_MISMATCH,
            4,
        ),
    )


def differential_vectors() -> tuple[DifferentialVector, ...]:
    """Return the complete frozen corpus in its deterministic declared order."""

    accepted = tuple(
        _accepted(vector_id, purpose, document)
        for vector_id, purpose, document in _accepted_documents()
    )
    return accepted + _rejected_vectors()
