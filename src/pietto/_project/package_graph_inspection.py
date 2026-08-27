"""Private Phase 59 package-graph integrity, inspection, and query boundary."""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from enum import StrEnum

import pietto._project.package_graph as graph
from pietto._project.model import _classify_project_definition

__all__: tuple[str, ...] = ()

_FORMAT_MARKER = b"pietto.package-graph.private.v1\0"


class PackageGraphInspectionDomain(StrEnum):
    """Closed canonical local-coordinate domains."""

    PACKAGE = "package"
    DEPENDENCY = "dependency"
    REQUIREMENT_COLLECTION = "requirement_collection"
    REQUIREMENT = "requirement"
    SELECTOR = "selector"
    CAPABILITY_EVALUATION = "capability_evaluation"
    CATALOG_EVIDENCE = "catalog_evidence"
    MODULE = "module"
    DECLARATION = "declaration"
    SEMANTIC_AUTHORITY = "semantic_authority"
    FIELD = "field"
    LET_BINDING = "let_binding"


class PackageGraphInspectionRecordKind(StrEnum):
    """Closed ordered canonical fact-record sections."""

    PACKAGE = "package"
    DEPENDENCY = "dependency"
    REQUIREMENT_COLLECTION = "requirement_collection"
    REQUIREMENT = "requirement"
    SELECTOR = "selector"
    CAPABILITY_EVALUATION = "capability_evaluation"
    CATALOG_EVIDENCE = "catalog_evidence"
    MODULE = "module"
    DECLARATION = "declaration"
    SEMANTIC_AUTHORITY = "semantic_authority"
    FIELD = "field"
    LET_BINDING = "let_binding"


class PackageGraphInspectionLinkKind(StrEnum):
    """Closed direct positive-topology relationship kinds."""

    DEPENDENCY = "dependency"
    REQUIREMENT = "requirement"
    SELECTOR = "selector"
    CAPABILITY_EVALUATION = "capability_evaluation"
    CATALOG_EVIDENCE = "catalog_evidence"
    MODULE = "module"
    DECLARATION = "declaration"
    FIELD = "field"
    LET_BINDING = "let_binding"
    SOURCE_LINEAGE = "source_lineage"
    PROJECTION_LINEAGE = "projection_lineage"
    EXPRESSION_LINEAGE = "expression_lineage"
    CURRENT_WINDOW_LINEAGE = "current_window_lineage"


class PackageGraphInspectionStateKind(StrEnum):
    """Closed typed negative/non-concrete inspection kinds."""

    RELATION_LINEAGE = "relation_lineage"
    LET_LINEAGE = "let_lineage"
    AGGREGATE_LINEAGE = "aggregate_lineage"
    EXPRESSION_LINEAGE = "expression_lineage"
    CURRENT_WINDOW_LINEAGE = "current_window_lineage"


class PackageGraphQueryDirection(StrEnum):
    """Closed directions over the one direct-link authority."""

    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"


class PackageGraphPureStatus(StrEnum):
    """Closed pure-evaluator outcomes for private canonical graph input."""

    OK = "ok"
    EMPTY_DOCUMENT = "empty_document"
    RECORD_ORDER = "record_order"
    ORDINAL_SEQUENCE = "ordinal_sequence"
    FIELD_SCHEMA = "field_schema"
    MALFORMED_REF = "malformed_ref"
    DUPLICATE_REF = "duplicate_ref"
    DANGLING_REF = "dangling_ref"
    WRONG_DOMAIN = "wrong_domain"
    OWNER_MISMATCH = "owner_mismatch"
    CANONICAL_MISMATCH = "canonical_mismatch"


@dataclass(frozen=True, slots=True)
class PackageGraphInspectionRef:
    """One canonical typed local coordinate with no runtime snapshot token."""

    domain: PackageGraphInspectionDomain
    positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.domain) is not PackageGraphInspectionDomain:
            raise TypeError("Inspection refs require an exact domain.")
        if type(self.positions) is not tuple or any(
            type(position) is not int for position in self.positions
        ):
            raise TypeError("Inspection refs require exact integer positions.")


type PackageGraphInspectionValue = (
    str
    | int
    | bool
    | bytes
    | None
    | tuple[str, ...]
    | tuple[int, ...]
    | PackageGraphInspectionRef
)


@dataclass(frozen=True, slots=True)
class PackageGraphInspectionField:
    """One named canonical fact value in declared order."""

    name: str
    value: PackageGraphInspectionValue

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise ValueError("Inspection field names must be non-empty text.")
        value = self.value
        if value is None or type(value) in {
            str,
            int,
            bool,
            bytes,
            PackageGraphInspectionRef,
        }:
            return
        if type(value) is not tuple or not (
            all(type(item) is str for item in value)
            or all(type(item) is int for item in value)
        ):
            raise TypeError("Inspection fields require exact canonical values.")


@dataclass(frozen=True, slots=True)
class PackageGraphInspectionRecord:
    """One canonical occurrence/fact record, never graph authority."""

    ordinal: int
    kind: PackageGraphInspectionRecordKind
    ref: PackageGraphInspectionRef
    fields: tuple[PackageGraphInspectionField, ...]

    def __post_init__(self) -> None:
        _require_ordinal(self.ordinal, "Inspection record")
        if type(self.kind) is not PackageGraphInspectionRecordKind:
            raise TypeError("Inspection records require an exact kind.")
        if type(self.ref) is not PackageGraphInspectionRef:
            raise TypeError("Inspection records require an exact ref.")
        _require_tuple(self.fields, PackageGraphInspectionField, "Inspection fields")


@dataclass(frozen=True, slots=True)
class PackageGraphInspectionLink:
    """One direct positive link derived from an exact Slice 6/8 witness."""

    ordinal: int
    kind: PackageGraphInspectionLinkKind
    source: PackageGraphInspectionRef
    target: PackageGraphInspectionRef
    witness_ref: PackageGraphInspectionRef | None
    fields: tuple[PackageGraphInspectionField, ...]

    def __post_init__(self) -> None:
        _require_ordinal(self.ordinal, "Inspection link")
        if type(self.kind) is not PackageGraphInspectionLinkKind:
            raise TypeError("Inspection links require an exact kind.")
        if (
            type(self.source) is not PackageGraphInspectionRef
            or type(self.target) is not PackageGraphInspectionRef
        ):
            raise TypeError("Inspection links require exact endpoint refs.")
        if (
            self.witness_ref is not None
            and type(self.witness_ref) is not PackageGraphInspectionRef
        ):
            raise TypeError("Inspection link witnesses require exact refs.")
        _require_tuple(self.fields, PackageGraphInspectionField, "Inspection fields")


@dataclass(frozen=True, slots=True)
class PackageGraphInspectionState:
    """One typed negative/non-concrete state, separate from positive links."""

    ordinal: int
    kind: PackageGraphInspectionStateKind
    owner: PackageGraphInspectionRef
    status: str
    reason: str | None
    fields: tuple[PackageGraphInspectionField, ...]

    def __post_init__(self) -> None:
        _require_ordinal(self.ordinal, "Inspection state")
        if type(self.kind) is not PackageGraphInspectionStateKind:
            raise TypeError("Inspection states require an exact kind.")
        if type(self.owner) is not PackageGraphInspectionRef:
            raise TypeError("Inspection states require an exact owner ref.")
        if type(self.status) is not str or not self.status:
            raise ValueError("Inspection states require a non-empty status.")
        if self.reason is not None and (
            type(self.reason) is not str or not self.reason
        ):
            raise ValueError("Inspection state reasons must be non-empty.")
        _require_tuple(self.fields, PackageGraphInspectionField, "Inspection fields")


@dataclass(frozen=True, slots=True)
class PackageGraphInspection:
    """Complete deterministic private graph inspection and canonical data."""

    records: tuple[PackageGraphInspectionRecord, ...]
    links: tuple[PackageGraphInspectionLink, ...]
    states: tuple[PackageGraphInspectionState, ...]
    canonical_bytes: bytes

    def __post_init__(self) -> None:
        _require_tuple(self.records, PackageGraphInspectionRecord, "Inspection records")
        _require_tuple(self.links, PackageGraphInspectionLink, "Inspection links")
        _require_tuple(self.states, PackageGraphInspectionState, "Inspection states")
        if type(self.canonical_bytes) is not bytes:
            raise TypeError("Inspection canonical data must be exact bytes.")


@dataclass(frozen=True, slots=True)
class PackageGraphPureOutcome:
    """One total pure-evaluator outcome without supplied-content echo."""

    status: PackageGraphPureStatus
    canonical_bytes: bytes | None = None
    record_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not PackageGraphPureStatus:
            raise TypeError("Pure outcomes require an exact status.")
        if self.canonical_bytes is not None and type(self.canonical_bytes) is not bytes:
            raise TypeError("Pure outcomes require exact canonical bytes.")
        if self.record_position is not None and type(self.record_position) is not int:
            raise TypeError("Pure outcome positions must be exact integers.")
        if self.status is PackageGraphPureStatus.OK:
            if self.canonical_bytes is None or self.record_position is not None:
                raise ValueError("Accepted pure outcomes require only canonical data.")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected pure outcomes forbid canonical data.")


@dataclass(frozen=True, slots=True)
class PackageGraphInspectionPath:
    """One on-demand occurrence-distinct canonical query path."""

    direction: PackageGraphQueryDirection
    start: PackageGraphInspectionRef
    end: PackageGraphInspectionRef
    links: tuple[PackageGraphInspectionLink, ...]

    def __post_init__(self) -> None:
        if type(self.direction) is not PackageGraphQueryDirection:
            raise TypeError("Inspection paths require an exact direction.")
        if (
            type(self.start) is not PackageGraphInspectionRef
            or type(self.end) is not PackageGraphInspectionRef
        ):
            raise TypeError("Inspection paths require exact endpoint refs.")
        _require_tuple(self.links, PackageGraphInspectionLink, "Inspection path links")
        if not self.links:
            raise ValueError("Inspection paths require at least one direct link.")
        current = self.start
        for link in self.links:
            source, target = _query_endpoints(link, self.direction)
            if source != current:
                raise ValueError("Inspection path links must be contiguous.")
            current = target
        if current != self.end:
            raise ValueError("Inspection paths must end at their exact ref.")


@dataclass(frozen=True, slots=True)
class PackageGraphInspectionWhyNot:
    """One positive path with its exact terminal non-success record."""

    path: PackageGraphInspectionPath
    terminal: PackageGraphInspectionRecord

    def __post_init__(self) -> None:
        if type(self.path) is not PackageGraphInspectionPath:
            raise TypeError("Why-not inspection requires an exact path.")
        if type(self.terminal) is not PackageGraphInspectionRecord:
            raise TypeError("Why-not inspection requires an exact terminal.")
        if self.terminal.ref != self.path.end or self.terminal.kind not in {
            PackageGraphInspectionRecordKind.CAPABILITY_EVALUATION,
            PackageGraphInspectionRecordKind.CATALOG_EVIDENCE,
        }:
            raise ValueError("Why-not terminal must attach to its exact path.")


_DOMAIN_LENGTHS = {
    PackageGraphInspectionDomain.PACKAGE: 1,
    PackageGraphInspectionDomain.DEPENDENCY: 2,
    PackageGraphInspectionDomain.REQUIREMENT_COLLECTION: 1,
    PackageGraphInspectionDomain.REQUIREMENT: 2,
    PackageGraphInspectionDomain.SELECTOR: 2,
    PackageGraphInspectionDomain.CAPABILITY_EVALUATION: 3,
    PackageGraphInspectionDomain.CATALOG_EVIDENCE: 3,
    PackageGraphInspectionDomain.MODULE: 2,
    PackageGraphInspectionDomain.DECLARATION: 3,
    PackageGraphInspectionDomain.SEMANTIC_AUTHORITY: 1,
    PackageGraphInspectionDomain.FIELD: 4,
    PackageGraphInspectionDomain.LET_BINDING: 4,
}

_RECORD_DOMAINS = {
    kind: PackageGraphInspectionDomain(kind.value)
    for kind in PackageGraphInspectionRecordKind
}

_RECORD_FIELDS = {
    PackageGraphInspectionRecordKind.PACKAGE: (
        "namespace",
        "name",
        "version",
        "content_digest",
        "role",
    ),
    PackageGraphInspectionRecordKind.DEPENDENCY: (
        "declaring_package",
        "resolved_package",
        "namespace",
        "name",
        "version",
        "content_digest",
        "locator_kind",
        "authored_path",
        "resolved_project_path",
    ),
    PackageGraphInspectionRecordKind.REQUIREMENT_COLLECTION: (
        "package",
        "declaration",
        "requirement_count",
        "selector_count",
    ),
    PackageGraphInspectionRecordKind.REQUIREMENT: (
        "package",
        "owner_namespace",
        "owner_name",
        "key",
    ),
    PackageGraphInspectionRecordKind.SELECTOR: (
        "package",
        "requirement",
        "scope",
    ),
    PackageGraphInspectionRecordKind.CAPABILITY_EVALUATION: (
        "requirement",
        "selector",
        "target_position",
        "outcome",
        "blockers",
        "evidence",
    ),
    PackageGraphInspectionRecordKind.CATALOG_EVIDENCE: (
        "selector",
        "capability",
        "target_position",
        "lookup_variant",
        "lookup_reason",
        "selected_catalog_position",
        "exact_group_position",
        "unmodeled_positions",
        "completeness_group_position",
        "evidence",
    ),
    PackageGraphInspectionRecordKind.MODULE: (
        "package",
        "path",
        "source_bytes",
    ),
    PackageGraphInspectionRecordKind.DECLARATION: (
        "module",
        "namespace",
        "kind",
        "name",
        "path",
        "line",
        "column",
        "end_line",
        "end_column",
    ),
    PackageGraphInspectionRecordKind.SEMANTIC_AUTHORITY: (
        "package",
        "module_count",
        "declaration_count",
    ),
    PackageGraphInspectionRecordKind.FIELD: (
        "declaration",
        "kind",
        "name",
        "type_name",
        "type_kind",
        "nullability",
        "result_role",
        "provenance_kind",
    ),
    PackageGraphInspectionRecordKind.LET_BINDING: (
        "declaration",
        "name",
        "value_type_name",
        "value_type_kind",
        "value_nullability",
        "scope_status",
        "scope_reason",
    ),
}

_LINK_FIELDS = {
    PackageGraphInspectionLinkKind.DEPENDENCY: (
        "authored_position",
        "authored_path",
    ),
    PackageGraphInspectionLinkKind.REQUIREMENT: ("position",),
    PackageGraphInspectionLinkKind.SELECTOR: ("position",),
    PackageGraphInspectionLinkKind.CAPABILITY_EVALUATION: (
        "target_position",
        "outcome",
    ),
    PackageGraphInspectionLinkKind.CATALOG_EVIDENCE: (
        "target_position",
        "lookup_variant",
    ),
    PackageGraphInspectionLinkKind.MODULE: ("position",),
    PackageGraphInspectionLinkKind.DECLARATION: ("position",),
    PackageGraphInspectionLinkKind.FIELD: ("position", "kind", "name"),
    PackageGraphInspectionLinkKind.LET_BINDING: ("position", "name"),
    PackageGraphInspectionLinkKind.SOURCE_LINEAGE: (),
    PackageGraphInspectionLinkKind.PROJECTION_LINEAGE: ("kind",),
    PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE: (
        "kind",
        "role",
        "container_position",
        "input_position",
    ),
    PackageGraphInspectionLinkKind.CURRENT_WINDOW_LINEAGE: (
        "role",
        "global_position",
        "role_position",
    ),
}

_STATE_FIELDS = {
    PackageGraphInspectionStateKind.RELATION_LINEAGE: (),
    PackageGraphInspectionStateKind.LET_LINEAGE: (),
    PackageGraphInspectionStateKind.AGGREGATE_LINEAGE: (),
    PackageGraphInspectionStateKind.EXPRESSION_LINEAGE: (
        "role",
        "container_position",
        "input_position",
    ),
    PackageGraphInspectionStateKind.CURRENT_WINDOW_LINEAGE: ("output_position",),
}

_LINK_DOMAINS = {
    PackageGraphInspectionLinkKind.DEPENDENCY: (
        {PackageGraphInspectionDomain.PACKAGE},
        {PackageGraphInspectionDomain.PACKAGE},
        PackageGraphInspectionDomain.DEPENDENCY,
    ),
    PackageGraphInspectionLinkKind.REQUIREMENT: (
        {PackageGraphInspectionDomain.PACKAGE},
        {PackageGraphInspectionDomain.REQUIREMENT},
        PackageGraphInspectionDomain.REQUIREMENT,
    ),
    PackageGraphInspectionLinkKind.SELECTOR: (
        {PackageGraphInspectionDomain.REQUIREMENT},
        {PackageGraphInspectionDomain.SELECTOR},
        PackageGraphInspectionDomain.SELECTOR,
    ),
    PackageGraphInspectionLinkKind.CAPABILITY_EVALUATION: (
        {
            PackageGraphInspectionDomain.REQUIREMENT,
            PackageGraphInspectionDomain.SELECTOR,
        },
        {PackageGraphInspectionDomain.CAPABILITY_EVALUATION},
        PackageGraphInspectionDomain.CAPABILITY_EVALUATION,
    ),
    PackageGraphInspectionLinkKind.CATALOG_EVIDENCE: (
        {PackageGraphInspectionDomain.CAPABILITY_EVALUATION},
        {PackageGraphInspectionDomain.CATALOG_EVIDENCE},
        PackageGraphInspectionDomain.CATALOG_EVIDENCE,
    ),
    PackageGraphInspectionLinkKind.MODULE: (
        {PackageGraphInspectionDomain.PACKAGE},
        {PackageGraphInspectionDomain.MODULE},
        PackageGraphInspectionDomain.MODULE,
    ),
    PackageGraphInspectionLinkKind.DECLARATION: (
        {PackageGraphInspectionDomain.MODULE},
        {PackageGraphInspectionDomain.DECLARATION},
        PackageGraphInspectionDomain.DECLARATION,
    ),
    PackageGraphInspectionLinkKind.FIELD: (
        {PackageGraphInspectionDomain.DECLARATION},
        {PackageGraphInspectionDomain.FIELD},
        PackageGraphInspectionDomain.FIELD,
    ),
    PackageGraphInspectionLinkKind.LET_BINDING: (
        {PackageGraphInspectionDomain.DECLARATION},
        {PackageGraphInspectionDomain.LET_BINDING},
        PackageGraphInspectionDomain.LET_BINDING,
    ),
    PackageGraphInspectionLinkKind.SOURCE_LINEAGE: (
        {PackageGraphInspectionDomain.FIELD},
        {PackageGraphInspectionDomain.FIELD},
        None,
    ),
    PackageGraphInspectionLinkKind.PROJECTION_LINEAGE: (
        {PackageGraphInspectionDomain.FIELD},
        {PackageGraphInspectionDomain.FIELD},
        None,
    ),
    PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE: (
        {
            PackageGraphInspectionDomain.FIELD,
            PackageGraphInspectionDomain.LET_BINDING,
        },
        {
            PackageGraphInspectionDomain.FIELD,
            PackageGraphInspectionDomain.LET_BINDING,
        },
        None,
    ),
    PackageGraphInspectionLinkKind.CURRENT_WINDOW_LINEAGE: (
        {PackageGraphInspectionDomain.FIELD},
        {
            PackageGraphInspectionDomain.FIELD,
            PackageGraphInspectionDomain.LET_BINDING,
            PackageGraphInspectionDomain.DECLARATION,
        },
        None,
    ),
}


def _require_ordinal(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} ordinal must be non-negative.")


def _require_tuple(values: object, item_type: type[object], label: str) -> None:
    if type(values) is not tuple or any(type(item) is not item_type for item in values):
        raise TypeError(f"{label} require an exact tuple.")


def _reject(
    status: PackageGraphPureStatus,
    position: int | None = None,
) -> PackageGraphPureOutcome:
    return PackageGraphPureOutcome(status=status, record_position=position)


def _field_names(
    fields: tuple[PackageGraphInspectionField, ...],
) -> tuple[str, ...]:
    return tuple(item.name for item in fields)


def _field_value(
    fields: tuple[PackageGraphInspectionField, ...],
    name: str,
) -> PackageGraphInspectionValue:
    matches = tuple(item.value for item in fields if item.name == name)
    if len(matches) != 1:
        raise ValueError("Canonical field lookup requires exactly one value.")
    return matches[0]


def _parent_ref(ref: PackageGraphInspectionRef) -> PackageGraphInspectionRef | None:
    positions = ref.positions
    if ref.domain is PackageGraphInspectionDomain.PACKAGE:
        return None
    if ref.domain in {
        PackageGraphInspectionDomain.DEPENDENCY,
        PackageGraphInspectionDomain.REQUIREMENT_COLLECTION,
        PackageGraphInspectionDomain.REQUIREMENT,
        PackageGraphInspectionDomain.SELECTOR,
        PackageGraphInspectionDomain.SEMANTIC_AUTHORITY,
        PackageGraphInspectionDomain.MODULE,
    }:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.PACKAGE,
            (positions[0],),
        )
    if ref.domain is PackageGraphInspectionDomain.CAPABILITY_EVALUATION:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.REQUIREMENT,
            positions[:2],
        )
    if ref.domain is PackageGraphInspectionDomain.CATALOG_EVIDENCE:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.SELECTOR,
            positions[:2],
        )
    if ref.domain is PackageGraphInspectionDomain.DECLARATION:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.MODULE,
            positions[:2],
        )
    if ref.domain in {
        PackageGraphInspectionDomain.FIELD,
        PackageGraphInspectionDomain.LET_BINDING,
    }:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.DECLARATION,
            positions[:3],
        )
    raise AssertionError("Unhandled canonical ref domain.")


def _record_owner_field(
    record: PackageGraphInspectionRecord,
) -> str | None:
    return {
        PackageGraphInspectionRecordKind.PACKAGE: None,
        PackageGraphInspectionRecordKind.DEPENDENCY: "declaring_package",
        PackageGraphInspectionRecordKind.REQUIREMENT_COLLECTION: "package",
        PackageGraphInspectionRecordKind.REQUIREMENT: "package",
        PackageGraphInspectionRecordKind.SELECTOR: "package",
        PackageGraphInspectionRecordKind.CAPABILITY_EVALUATION: "requirement",
        PackageGraphInspectionRecordKind.CATALOG_EVIDENCE: "selector",
        PackageGraphInspectionRecordKind.MODULE: "package",
        PackageGraphInspectionRecordKind.DECLARATION: "module",
        PackageGraphInspectionRecordKind.SEMANTIC_AUTHORITY: "package",
        PackageGraphInspectionRecordKind.FIELD: "declaration",
        PackageGraphInspectionRecordKind.LET_BINDING: "declaration",
    }[record.kind]


def _validate_record_relations(
    record: PackageGraphInspectionRecord,
    refs: set[PackageGraphInspectionRef],
) -> PackageGraphPureStatus | None:
    parent = _parent_ref(record.ref)
    if parent is not None and parent not in refs:
        return PackageGraphPureStatus.DANGLING_REF
    owner_name = _record_owner_field(record)
    if owner_name is not None:
        owner = _field_value(record.fields, owner_name)
        if type(owner) is not PackageGraphInspectionRef:
            return PackageGraphPureStatus.WRONG_DOMAIN
        if owner != parent:
            return PackageGraphPureStatus.OWNER_MISMATCH

    if record.kind is PackageGraphInspectionRecordKind.DEPENDENCY:
        target = _field_value(record.fields, "resolved_package")
        if (
            type(target) is not PackageGraphInspectionRef
            or target.domain is not PackageGraphInspectionDomain.PACKAGE
        ):
            return PackageGraphPureStatus.WRONG_DOMAIN
        if target not in refs:
            return PackageGraphPureStatus.DANGLING_REF
    elif record.kind is PackageGraphInspectionRecordKind.SELECTOR:
        requirement = _field_value(record.fields, "requirement")
        if (
            type(requirement) is not PackageGraphInspectionRef
            or requirement.domain is not PackageGraphInspectionDomain.REQUIREMENT
            or requirement.positions[0] != record.ref.positions[0]
        ):
            return PackageGraphPureStatus.OWNER_MISMATCH
        if requirement not in refs:
            return PackageGraphPureStatus.DANGLING_REF
    elif record.kind is PackageGraphInspectionRecordKind.CAPABILITY_EVALUATION:
        selector = _field_value(record.fields, "selector")
        if selector is not None:
            if (
                type(selector) is not PackageGraphInspectionRef
                or selector.domain is not PackageGraphInspectionDomain.SELECTOR
                or selector.positions[0] != record.ref.positions[0]
            ):
                return PackageGraphPureStatus.WRONG_DOMAIN
            if selector not in refs:
                return PackageGraphPureStatus.DANGLING_REF
    elif record.kind is PackageGraphInspectionRecordKind.CATALOG_EVIDENCE:
        capability = _field_value(record.fields, "capability")
        if (
            type(capability) is not PackageGraphInspectionRef
            or capability.domain
            is not PackageGraphInspectionDomain.CAPABILITY_EVALUATION
            or capability.positions[0] != record.ref.positions[0]
            or capability.positions[2] != record.ref.positions[2]
        ):
            return PackageGraphPureStatus.OWNER_MISMATCH
        if capability not in refs:
            return PackageGraphPureStatus.DANGLING_REF
    return None


def _validate_link_relations(
    link: PackageGraphInspectionLink,
    records: dict[PackageGraphInspectionRef, PackageGraphInspectionRecord],
) -> PackageGraphPureStatus | None:
    allowed_sources, allowed_targets, witness_domain = _LINK_DOMAINS[link.kind]
    if link.source.domain not in allowed_sources or link.target.domain not in (
        allowed_targets
    ):
        return PackageGraphPureStatus.WRONG_DOMAIN
    if link.source not in records or link.target not in records:
        return PackageGraphPureStatus.DANGLING_REF
    if witness_domain is None:
        if link.witness_ref is not None:
            return PackageGraphPureStatus.WRONG_DOMAIN
    elif (
        link.witness_ref is None
        or link.witness_ref.domain is not witness_domain
        or link.witness_ref not in records
    ):
        return PackageGraphPureStatus.DANGLING_REF

    if (
        link.kind
        in {
            PackageGraphInspectionLinkKind.SOURCE_LINEAGE,
            PackageGraphInspectionLinkKind.PROJECTION_LINEAGE,
            PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE,
            PackageGraphInspectionLinkKind.CURRENT_WINDOW_LINEAGE,
        }
        and link.source.positions[0] != link.target.positions[0]
    ):
        return PackageGraphPureStatus.OWNER_MISMATCH

    witness = None if link.witness_ref is None else records[link.witness_ref]
    if link.kind is PackageGraphInspectionLinkKind.DEPENDENCY:
        assert witness is not None
        if (
            _field_value(witness.fields, "declaring_package") != link.source
            or _field_value(witness.fields, "resolved_package") != link.target
        ):
            return PackageGraphPureStatus.OWNER_MISMATCH
    elif link.kind is PackageGraphInspectionLinkKind.SELECTOR:
        assert witness is not None
        if _field_value(witness.fields, "requirement") != link.source:
            return PackageGraphPureStatus.OWNER_MISMATCH
    elif link.kind is PackageGraphInspectionLinkKind.CAPABILITY_EVALUATION:
        assert witness is not None
        expected_source = _field_value(witness.fields, "selector") or _field_value(
            witness.fields,
            "requirement",
        )
        if expected_source != link.source:
            return PackageGraphPureStatus.OWNER_MISMATCH
    elif link.kind is PackageGraphInspectionLinkKind.CATALOG_EVIDENCE:
        assert witness is not None
        if _field_value(witness.fields, "capability") != link.source:
            return PackageGraphPureStatus.OWNER_MISMATCH
    elif witness is not None and link.kind in {
        PackageGraphInspectionLinkKind.REQUIREMENT,
        PackageGraphInspectionLinkKind.MODULE,
        PackageGraphInspectionLinkKind.DECLARATION,
        PackageGraphInspectionLinkKind.FIELD,
        PackageGraphInspectionLinkKind.LET_BINDING,
    }:
        owner_name = _record_owner_field(witness)
        if (
            owner_name is None
            or _field_value(witness.fields, owner_name) != link.source
        ):
            return PackageGraphPureStatus.OWNER_MISMATCH
        if witness.ref != link.target:
            return PackageGraphPureStatus.OWNER_MISMATCH
    return None


def _evaluate_package_graph_inspection(
    inspection: PackageGraphInspection,
) -> PackageGraphPureOutcome:
    """Evaluate explicit canonical graph input without ambient authority."""

    if type(inspection) is not PackageGraphInspection:
        raise TypeError("Graph pure evaluation requires an exact inspection.")
    if not inspection.records:
        return _reject(PackageGraphPureStatus.EMPTY_DOCUMENT)
    if tuple(item.ordinal for item in inspection.records) != tuple(
        range(len(inspection.records))
    ):
        return _reject(PackageGraphPureStatus.ORDINAL_SEQUENCE)
    if tuple(item.ordinal for item in inspection.links) != tuple(
        range(len(inspection.links))
    ) or tuple(item.ordinal for item in inspection.states) != tuple(
        range(len(inspection.states))
    ):
        return _reject(PackageGraphPureStatus.ORDINAL_SEQUENCE)

    kind_order = tuple(PackageGraphInspectionRecordKind)
    positions = tuple(kind_order.index(item.kind) for item in inspection.records)
    if positions != tuple(sorted(positions)):
        return _reject(PackageGraphPureStatus.RECORD_ORDER)

    records: dict[PackageGraphInspectionRef, PackageGraphInspectionRecord] = {}
    for position, record in enumerate(inspection.records):
        if _field_names(record.fields) != _RECORD_FIELDS[record.kind]:
            return _reject(PackageGraphPureStatus.FIELD_SCHEMA, position)
        if (
            record.ref.domain is not _RECORD_DOMAINS[record.kind]
            or len(record.ref.positions) != _DOMAIN_LENGTHS[record.ref.domain]
            or any(value < 0 for value in record.ref.positions)
        ):
            return _reject(PackageGraphPureStatus.MALFORMED_REF, position)
        if record.ref in records:
            return _reject(PackageGraphPureStatus.DUPLICATE_REF, position)
        records[record.ref] = record

    refs = set(records)
    for position, record in enumerate(inspection.records):
        rejection = _validate_record_relations(record, refs)
        if rejection is not None:
            return _reject(rejection, position)
    for position, link in enumerate(inspection.links):
        if _field_names(link.fields) != _LINK_FIELDS[link.kind]:
            return _reject(PackageGraphPureStatus.FIELD_SCHEMA, position)
        rejection = _validate_link_relations(link, records)
        if rejection is not None:
            return _reject(rejection, position)
    for position, state in enumerate(inspection.states):
        if _field_names(state.fields) != _STATE_FIELDS[state.kind]:
            return _reject(PackageGraphPureStatus.FIELD_SCHEMA, position)
        if (
            state.owner.domain is not PackageGraphInspectionDomain.DECLARATION
            or state.owner not in records
        ):
            return _reject(PackageGraphPureStatus.DANGLING_REF, position)

    canonical_bytes = _encode_inspection(inspection)
    if inspection.canonical_bytes != canonical_bytes:
        return _reject(PackageGraphPureStatus.CANONICAL_MISMATCH)
    return PackageGraphPureOutcome(
        status=PackageGraphPureStatus.OK,
        canonical_bytes=canonical_bytes,
    )


def _require_valid_inspection(inspection: PackageGraphInspection) -> None:
    outcome = _evaluate_package_graph_inspection(inspection)
    if outcome.status is not PackageGraphPureStatus.OK:
        raise ValueError(
            "Package graph inspection must be valid: "
            f"{outcome.status.value} at {outcome.record_position}."
        )


def _query_endpoints(
    link: PackageGraphInspectionLink,
    direction: PackageGraphQueryDirection,
) -> tuple[PackageGraphInspectionRef, PackageGraphInspectionRef]:
    if direction is PackageGraphQueryDirection.UPSTREAM:
        return link.source, link.target
    return link.target, link.source


def _query_package_graph_direct_upstream(
    inspection: PackageGraphInspection,
    ref: PackageGraphInspectionRef,
) -> tuple[PackageGraphInspectionLink, ...]:
    _require_valid_inspection(inspection)
    _require_query_ref(inspection, ref)
    return tuple(link for link in inspection.links if link.source == ref)


def _query_package_graph_direct_downstream(
    inspection: PackageGraphInspection,
    ref: PackageGraphInspectionRef,
) -> tuple[PackageGraphInspectionLink, ...]:
    _require_valid_inspection(inspection)
    _require_query_ref(inspection, ref)
    return tuple(link for link in inspection.links if link.target == ref)


def _require_query_ref(
    inspection: PackageGraphInspection,
    ref: PackageGraphInspectionRef,
) -> None:
    if type(ref) is not PackageGraphInspectionRef:
        raise TypeError("Graph queries require an exact inspection ref.")
    if not any(record.ref == ref for record in inspection.records):
        raise ValueError("Graph query ref does not exist in the inspection.")


def _query_package_graph_paths(
    inspection: PackageGraphInspection,
    start: PackageGraphInspectionRef,
    end: PackageGraphInspectionRef,
    direction: PackageGraphQueryDirection = PackageGraphQueryDirection.UPSTREAM,
) -> tuple[PackageGraphInspectionPath, ...]:
    """Enumerate all requested paths on demand in direct-link order."""

    _require_valid_inspection(inspection)
    _require_query_ref(inspection, start)
    _require_query_ref(inspection, end)
    if type(direction) is not PackageGraphQueryDirection:
        raise TypeError("Graph path queries require an exact direction.")
    if start == end:
        return ()

    paths: list[PackageGraphInspectionPath] = []

    # ponytail: local private documents scan direct links; add an index only after
    # measurement, and keep it derived from this tuple.
    def extend(
        current: PackageGraphInspectionRef,
        prefix: tuple[PackageGraphInspectionLink, ...],
        visited: tuple[PackageGraphInspectionRef, ...],
    ) -> None:
        for link in inspection.links:
            source, target = _query_endpoints(link, direction)
            if source != current:
                continue
            extended = (*prefix, link)
            if target == end:
                paths.append(
                    PackageGraphInspectionPath(
                        direction=direction,
                        start=start,
                        end=end,
                        links=extended,
                    )
                )
                continue
            if target in visited:
                continue
            extend(target, extended, (*visited, target))

    extend(start, (), (start,))
    return tuple(paths)


def _query_package_graph_why(
    inspection: PackageGraphInspection,
    start: PackageGraphInspectionRef,
    end: PackageGraphInspectionRef,
) -> tuple[PackageGraphInspectionPath, ...]:
    return _query_package_graph_paths(inspection, start, end)


def _query_package_graph_why_not(
    inspection: PackageGraphInspection,
    start: PackageGraphInspectionRef,
    end: PackageGraphInspectionRef,
) -> tuple[PackageGraphInspectionWhyNot, ...]:
    paths = _query_package_graph_why(inspection, start, end)
    terminal_matches = tuple(
        record for record in inspection.records if record.ref == end
    )
    if len(terminal_matches) != 1:
        raise ValueError("Why-not terminal must resolve exactly once.")
    terminal = terminal_matches[0]
    if terminal.kind is PackageGraphInspectionRecordKind.CAPABILITY_EVALUATION:
        if _field_value(terminal.fields, "outcome") == "satisfied":
            return ()
    elif terminal.kind is PackageGraphInspectionRecordKind.CATALOG_EVIDENCE:
        if (
            _field_value(terminal.fields, "lookup_variant") == "found"
            and _field_value(terminal.fields, "selected_catalog_position") is not None
        ):
            return ()
    else:
        raise TypeError("Why-not queries require capability or catalog terminals.")
    return tuple(PackageGraphInspectionWhyNot(path, terminal) for path in paths)


def _validate_package_graph_integrity(snapshot: graph.PackageGraphSnapshot) -> None:
    """Re-run every Slice 2--8 invariant without mutating or repairing input."""

    if type(snapshot) is not graph.PackageGraphSnapshot:
        raise TypeError("Graph integrity requires an exact snapshot.")
    values = {
        item.name: getattr(snapshot, item.name)
        for item in dataclass_fields(graph.PackageGraphSnapshot)
    }
    graph.PackageGraphSnapshot(**values)
    for step in graph._package_graph_direct_provenance_steps(snapshot):
        source = graph._direct_step_source(step)
        target = graph._direct_step_target(step)
        graph._resolve_provenance_ref(snapshot, source)
        graph._resolve_provenance_ref(snapshot, target)


def _inspection_ref(ref: object) -> PackageGraphInspectionRef:
    if type(ref) is graph.PackageGraphPackageRef:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.PACKAGE,
            (ref.position,),
        )
    if type(ref) is graph.PackageGraphDependencyRef:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.DEPENDENCY,
            (ref.declaring_package.position, ref.declaration_position),
        )
    if type(ref) is graph.PackageGraphRequirementRef:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.REQUIREMENT,
            (ref.package.position, ref.position),
        )
    if type(ref) is graph.PackageGraphSelectorRef:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.SELECTOR,
            (ref.package.position, ref.position),
        )
    if type(ref) is graph.PackageGraphCapabilityEvaluationRef:
        requirement = ref.requirement
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.CAPABILITY_EVALUATION,
            (
                requirement.package.position,
                requirement.position,
                ref.target_position,
            ),
        )
    if type(ref) is graph.PackageGraphCatalogEvidenceRef:
        selector = ref.selector
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.CATALOG_EVIDENCE,
            (
                selector.package.position,
                selector.position,
                ref.target_position,
            ),
        )
    if type(ref) is graph.PackageGraphModuleRef:
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.MODULE,
            (ref.package.position, ref.position),
        )
    if type(ref) is graph.PackageGraphDeclarationRef:
        module = ref.module
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.DECLARATION,
            (module.package.position, module.position, ref.position),
        )
    if type(ref) is graph.PackageGraphFieldRef:
        declaration = ref.declaration
        module = declaration.module
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.FIELD,
            (
                module.package.position,
                module.position,
                declaration.position,
                ref.position,
            ),
        )
    if type(ref) is graph.PackageGraphLetRef:
        declaration = ref.declaration
        module = declaration.module
        return PackageGraphInspectionRef(
            PackageGraphInspectionDomain.LET_BINDING,
            (
                module.package.position,
                module.position,
                declaration.position,
                ref.position,
            ),
        )
    raise TypeError("Canonical inspection requires an exact supported graph ref.")


def _inspection_field(
    name: str,
    value: PackageGraphInspectionValue,
) -> PackageGraphInspectionField:
    return PackageGraphInspectionField(name, value)


def _append_record(
    records: list[PackageGraphInspectionRecord],
    kind: PackageGraphInspectionRecordKind,
    ref: PackageGraphInspectionRef,
    *pairs: tuple[str, PackageGraphInspectionValue],
) -> None:
    records.append(
        PackageGraphInspectionRecord(
            ordinal=len(records),
            kind=kind,
            ref=ref,
            fields=tuple(_inspection_field(name, value) for name, value in pairs),
        )
    )


def _capability_outcome(evaluation: graph.PackageGraphCapabilityEvaluation) -> str:
    evidence = evaluation.evidence
    if type(evidence) is graph.CapabilityRequirementCheck:
        return evidence.status.value
    if type(evidence) is graph.PackageCapabilityRequirementsBlocked:
        return "blocked"
    raise TypeError("Capability inspection requires exact terminal evidence.")


def _capability_blockers(
    evaluation: graph.PackageGraphCapabilityEvaluation,
) -> tuple[str, ...]:
    evidence = evaluation.evidence
    if type(evidence) is graph.PackageCapabilityRequirementsBlocked:
        return tuple(item.kind.value for item in evidence.blockers)
    return ()


def _build_inspection_records(
    snapshot: graph.PackageGraphSnapshot,
) -> tuple[PackageGraphInspectionRecord, ...]:
    records: list[PackageGraphInspectionRecord] = []
    for package in snapshot.packages:
        coordinate = package.coordinate
        _append_record(
            records,
            PackageGraphInspectionRecordKind.PACKAGE,
            _inspection_ref(package.ref),
            ("namespace", coordinate.identity.namespace),
            ("name", coordinate.identity.name),
            ("version", coordinate.exact_version),
            ("content_digest", package.content_digest),
            ("role", package.role.value),
        )
    for dependency in snapshot.dependencies:
        witness = dependency.witness
        declaration = witness.declaration
        _append_record(
            records,
            PackageGraphInspectionRecordKind.DEPENDENCY,
            _inspection_ref(dependency.ref),
            ("declaring_package", _inspection_ref(dependency.declaring_package)),
            ("resolved_package", _inspection_ref(dependency.resolved_package)),
            ("namespace", witness.coordinate.identity.namespace),
            ("name", witness.coordinate.identity.name),
            ("version", witness.coordinate.exact_version),
            ("content_digest", witness.content_digest_pin),
            ("locator_kind", witness.locator_kind.value),
            ("authored_path", declaration.path),
            ("resolved_project_path", witness.resolved_project_path),
        )
    for collection in snapshot.requirement_collections:
        package = collection.package
        _append_record(
            records,
            PackageGraphInspectionRecordKind.REQUIREMENT_COLLECTION,
            PackageGraphInspectionRef(
                PackageGraphInspectionDomain.REQUIREMENT_COLLECTION,
                (package.position,),
            ),
            ("package", _inspection_ref(package)),
            ("declaration", collection.declaration.value),
            (
                "requirement_count",
                0
                if collection.binding is None
                else len(collection.binding.requirements.occurrences),
            ),
            (
                "selector_count",
                0
                if collection.selectors is None
                else len(collection.selectors.occurrences),
            ),
        )
    for requirement in snapshot.requirements:
        owner = requirement.witness.owner
        _append_record(
            records,
            PackageGraphInspectionRecordKind.REQUIREMENT,
            _inspection_ref(requirement.ref),
            ("package", _inspection_ref(requirement.package)),
            ("owner_namespace", owner.namespace),
            ("owner_name", owner.name),
            ("key", _encode_semantic_value(requirement.witness.key)),
        )
    for selector in snapshot.selectors:
        _append_record(
            records,
            PackageGraphInspectionRecordKind.SELECTOR,
            _inspection_ref(selector.ref),
            ("package", _inspection_ref(selector.package)),
            ("requirement", _inspection_ref(selector.requirement)),
            ("scope", _encode_semantic_value(selector.witness.selector.scope)),
        )
    for evaluation in snapshot.capability_evaluations:
        _append_record(
            records,
            PackageGraphInspectionRecordKind.CAPABILITY_EVALUATION,
            _inspection_ref(evaluation.ref),
            ("requirement", _inspection_ref(evaluation.ref.requirement)),
            (
                "selector",
                None
                if evaluation.selector is None
                else _inspection_ref(evaluation.selector),
            ),
            ("target_position", evaluation.ref.target_position),
            ("outcome", _capability_outcome(evaluation)),
            ("blockers", _capability_blockers(evaluation)),
            ("evidence", evaluation.facts.canonical_bytes),
        )
    for evidence in snapshot.catalog_evidence:
        provider = evidence.provider
        _append_record(
            records,
            PackageGraphInspectionRecordKind.CATALOG_EVIDENCE,
            _inspection_ref(evidence.ref),
            ("selector", _inspection_ref(evidence.ref.selector)),
            ("capability", _inspection_ref(evidence.capability)),
            ("target_position", evidence.ref.target_position),
            ("lookup_variant", provider.lookup.variant.value),
            (
                "lookup_reason",
                None
                if provider.lookup.reason is None
                else provider.lookup.reason.value,
            ),
            ("selected_catalog_position", provider.selected_catalog_position),
            ("exact_group_position", provider.exact_group_position),
            ("unmodeled_positions", provider.unmodeled_blocker_entry_positions),
            ("completeness_group_position", provider.completeness_group_position),
            ("evidence", evidence.facts.canonical_bytes),
        )
    for module in snapshot.modules:
        _append_record(
            records,
            PackageGraphInspectionRecordKind.MODULE,
            _inspection_ref(module.ref),
            ("package", _inspection_ref(module.package)),
            ("path", module.witness.identity.path),
            ("source_bytes", module.witness.source.content),
        )
    for declaration in snapshot.declarations:
        namespace, kind = _classify_project_definition(declaration.witness)
        span = declaration.witness.span
        _append_record(
            records,
            PackageGraphInspectionRecordKind.DECLARATION,
            _inspection_ref(declaration.ref),
            ("module", _inspection_ref(declaration.module)),
            ("namespace", namespace.value),
            ("kind", kind.value),
            ("name", declaration.witness.name),
            ("path", span.path),
            ("line", span.line),
            ("column", span.column),
            ("end_line", span.end_line),
            ("end_column", span.end_column),
        )
    for authority in snapshot.semantic_authorities:
        _append_record(
            records,
            PackageGraphInspectionRecordKind.SEMANTIC_AUTHORITY,
            PackageGraphInspectionRef(
                PackageGraphInspectionDomain.SEMANTIC_AUTHORITY,
                (authority.package.position,),
            ),
            ("package", _inspection_ref(authority.package)),
            ("module_count", len(authority.witness.module_assets)),
            ("declaration_count", len(authority.witness.declaration_assets)),
        )
    for field in snapshot.fields:
        semantic = field.semantic_field
        provenance = None if semantic is None else semantic.provenance
        _append_record(
            records,
            PackageGraphInspectionRecordKind.FIELD,
            _inspection_ref(field.ref),
            ("declaration", _inspection_ref(field.declaration)),
            ("kind", field.kind.value),
            ("name", field.name),
            ("type_name", None if semantic is None else semantic.resolved_type.name),
            (
                "type_kind",
                None if semantic is None else semantic.resolved_type.kind.value,
            ),
            (
                "nullability",
                None if semantic is None else semantic.nullability.value,
            ),
            ("result_role", None if semantic is None else semantic.result_role.value),
            ("provenance_kind", None if provenance is None else provenance.kind.value),
        )
    for binding in snapshot.let_bindings:
        value_type = binding.witness.value_type
        scope = binding.witness.scope_facts
        _append_record(
            records,
            PackageGraphInspectionRecordKind.LET_BINDING,
            _inspection_ref(binding.ref),
            ("declaration", _inspection_ref(binding.declaration)),
            ("name", binding.witness.binding.name),
            (
                "value_type_name",
                None if value_type is None else value_type.resolved_type.name,
            ),
            ("value_type_kind", None if value_type is None else value_type.kind.value),
            (
                "value_nullability",
                None if value_type is None else value_type.nullability.value,
            ),
            ("scope_status", scope.status.value),
            ("scope_reason", scope.reason.value),
        )
    return tuple(records)


def _link_kind(
    witness: graph.PackageGraphDirectProvenanceWitness,
) -> PackageGraphInspectionLinkKind:
    if type(witness) is graph.PackageGraphDependency:
        return PackageGraphInspectionLinkKind.DEPENDENCY
    if type(witness) is graph.PackageGraphRequirement:
        return PackageGraphInspectionLinkKind.REQUIREMENT
    if type(witness) is graph.PackageGraphSelector:
        return PackageGraphInspectionLinkKind.SELECTOR
    if type(witness) is graph.PackageGraphCapabilityEvaluation:
        return PackageGraphInspectionLinkKind.CAPABILITY_EVALUATION
    if type(witness) is graph.PackageGraphCatalogEvidence:
        return PackageGraphInspectionLinkKind.CATALOG_EVIDENCE
    if type(witness) is graph.PackageGraphModule:
        return PackageGraphInspectionLinkKind.MODULE
    if type(witness) is graph.PackageGraphDeclaration:
        return PackageGraphInspectionLinkKind.DECLARATION
    if type(witness) is graph.PackageGraphField:
        return PackageGraphInspectionLinkKind.FIELD
    if type(witness) is graph.PackageGraphLetBinding:
        return PackageGraphInspectionLinkKind.LET_BINDING
    if type(witness) is graph.PackageGraphSourceLineage:
        return PackageGraphInspectionLinkKind.SOURCE_LINEAGE
    if type(witness) is graph.PackageGraphProjectionLineage:
        return PackageGraphInspectionLinkKind.PROJECTION_LINEAGE
    if type(witness) is graph.PackageGraphExpressionLineage:
        return PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    if type(witness) is graph.PackageGraphCurrentWindowLineage:
        return PackageGraphInspectionLinkKind.CURRENT_WINDOW_LINEAGE
    raise AssertionError("Unsupported direct provenance witness.")


def _link_witness_ref(
    witness: graph.PackageGraphDirectProvenanceWitness,
) -> PackageGraphInspectionRef | None:
    if type(witness) is graph.PackageGraphSourceLineage:
        return None
    if type(witness) is graph.PackageGraphProjectionLineage:
        return None
    if type(witness) is graph.PackageGraphExpressionLineage:
        return None
    if type(witness) is graph.PackageGraphCurrentWindowLineage:
        return None
    if type(witness) is graph.PackageGraphDependency:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphRequirement:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphSelector:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphCapabilityEvaluation:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphCatalogEvidence:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphModule:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphDeclaration:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphField:
        return _inspection_ref(witness.ref)
    if type(witness) is graph.PackageGraphLetBinding:
        return _inspection_ref(witness.ref)
    raise AssertionError("Unsupported direct provenance witness.")


def _link_fields(
    witness: graph.PackageGraphDirectProvenanceWitness,
) -> tuple[PackageGraphInspectionField, ...]:
    if type(witness) is graph.PackageGraphDependency:
        return (
            _inspection_field("authored_position", witness.ref.declaration_position),
            _inspection_field("authored_path", witness.witness.declaration.path),
        )
    if type(witness) is graph.PackageGraphRequirement:
        return (_inspection_field("position", witness.ref.position),)
    if type(witness) is graph.PackageGraphSelector:
        return (_inspection_field("position", witness.ref.position),)
    if type(witness) is graph.PackageGraphCapabilityEvaluation:
        return (
            _inspection_field("target_position", witness.ref.target_position),
            _inspection_field("outcome", _capability_outcome(witness)),
        )
    if type(witness) is graph.PackageGraphCatalogEvidence:
        return (
            _inspection_field("target_position", witness.ref.target_position),
            _inspection_field("lookup_variant", witness.provider.lookup.variant.value),
        )
    if type(witness) is graph.PackageGraphModule:
        return (_inspection_field("position", witness.ref.position),)
    if type(witness) is graph.PackageGraphDeclaration:
        return (_inspection_field("position", witness.ref.position),)
    if type(witness) is graph.PackageGraphField:
        return (
            _inspection_field("position", witness.ref.position),
            _inspection_field("kind", witness.kind.value),
            _inspection_field("name", witness.name),
        )
    if type(witness) is graph.PackageGraphLetBinding:
        return (
            _inspection_field("position", witness.ref.position),
            _inspection_field("name", witness.witness.binding.name),
        )
    if type(witness) is graph.PackageGraphSourceLineage:
        return ()
    if type(witness) is graph.PackageGraphProjectionLineage:
        return (_inspection_field("kind", witness.kind.value),)
    if type(witness) is graph.PackageGraphExpressionLineage:
        return (
            _inspection_field("kind", witness.kind.value),
            _inspection_field("role", witness.role.value),
            _inspection_field("container_position", witness.container_position),
            _inspection_field("input_position", witness.input_position),
        )
    if type(witness) is graph.PackageGraphCurrentWindowLineage:
        return (
            _inspection_field("role", witness.role.value),
            _inspection_field("global_position", witness.global_position),
            _inspection_field("role_position", witness.role_position),
        )
    raise AssertionError("Unsupported direct provenance witness.")


def _build_inspection_links(
    snapshot: graph.PackageGraphSnapshot,
) -> tuple[PackageGraphInspectionLink, ...]:
    links: list[PackageGraphInspectionLink] = []
    for step in graph._package_graph_direct_provenance_steps(snapshot):
        witness = step.witness
        links.append(
            PackageGraphInspectionLink(
                ordinal=len(links),
                kind=_link_kind(witness),
                source=_inspection_ref(graph._direct_step_source(step)),
                target=_inspection_ref(graph._direct_step_target(step)),
                witness_ref=_link_witness_ref(witness),
                fields=_link_fields(witness),
            )
        )
    return tuple(links)


def _append_state(
    states: list[PackageGraphInspectionState],
    kind: PackageGraphInspectionStateKind,
    owner: graph.PackageGraphDeclarationRef,
    status: str,
    reason: str | None,
    *pairs: tuple[str, PackageGraphInspectionValue],
) -> None:
    states.append(
        PackageGraphInspectionState(
            ordinal=len(states),
            kind=kind,
            owner=_inspection_ref(owner),
            status=status,
            reason=reason,
            fields=tuple(_inspection_field(name, value) for name, value in pairs),
        )
    )


def _build_inspection_states(
    snapshot: graph.PackageGraphSnapshot,
) -> tuple[PackageGraphInspectionState, ...]:
    states: list[PackageGraphInspectionState] = []
    for state in snapshot.relation_lineage_states:
        _append_state(
            states,
            PackageGraphInspectionStateKind.RELATION_LINEAGE,
            state.declaration,
            state.status.value,
            state.reason.value,
        )
    for state in snapshot.let_lineage_states:
        _append_state(
            states,
            PackageGraphInspectionStateKind.LET_LINEAGE,
            state.declaration,
            state.status.value,
            state.reason.value,
        )
    for state in snapshot.aggregate_lineage_states:
        _append_state(
            states,
            PackageGraphInspectionStateKind.AGGREGATE_LINEAGE,
            state.declaration,
            state.status.value,
            state.reason.value,
        )
    for state in snapshot.expression_lineage_states:
        _append_state(
            states,
            PackageGraphInspectionStateKind.EXPRESSION_LINEAGE,
            state.declaration,
            state.status.value,
            None,
            ("role", state.role.value),
            ("container_position", state.container_position),
            ("input_position", state.input_position),
        )
    for state in snapshot.current_window_lineage_states:
        _append_state(
            states,
            PackageGraphInspectionStateKind.CURRENT_WINDOW_LINEAGE,
            state.declaration,
            state.status.value,
            state.reason,
            ("output_position", state.output_position),
        )
    return tuple(states)


def _inspect_package_graph(
    snapshot: graph.PackageGraphSnapshot,
) -> PackageGraphInspection:
    """Build one complete private canonical inspection from exact graph authority."""

    _validate_package_graph_integrity(snapshot)
    records = _build_inspection_records(snapshot)
    links = _build_inspection_links(snapshot)
    states = _build_inspection_states(snapshot)
    provisional = PackageGraphInspection(records, links, states, b"")
    inspection = PackageGraphInspection(
        records,
        links,
        states,
        _encode_inspection(provisional),
    )
    _require_valid_inspection(inspection)
    return inspection


def _frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, "big") + payload


def _encode_ref(ref: PackageGraphInspectionRef) -> bytes:
    return b"".join(
        (
            _frame(ref.domain.value.encode("ascii")),
            _frame(str(len(ref.positions)).encode("ascii")),
            *(_frame(str(position).encode("ascii")) for position in ref.positions),
        )
    )


def _encode_value(value: PackageGraphInspectionValue) -> bytes:
    if value is None:
        return b"n"
    if type(value) is bool:
        return b"b1" if value else b"b0"
    if type(value) is int:
        return b"i" + str(value).encode("ascii")
    if type(value) is str:
        return b"s" + value.encode("utf-8", "surrogatepass")
    if type(value) is bytes:
        return b"y" + value
    if type(value) is PackageGraphInspectionRef:
        return b"r" + _encode_ref(value)
    if type(value) is tuple:
        return b"q" + b"".join(_frame(_encode_value(item)) for item in value)
    raise TypeError("Canonical inspection cannot encode this value.")


def _encode_fields(fields: tuple[PackageGraphInspectionField, ...]) -> bytes:
    return b"".join(
        _frame(item.name.encode("utf-8")) + _frame(_encode_value(item.value))
        for item in fields
    )


def _encode_inspection(inspection: PackageGraphInspection) -> bytes:
    records = b"".join(
        _frame(
            b"R"
            + _frame(str(record.ordinal).encode("ascii"))
            + _frame(record.kind.value.encode("ascii"))
            + _frame(_encode_ref(record.ref))
            + _frame(_encode_fields(record.fields))
        )
        for record in inspection.records
    )
    links = b"".join(
        _frame(
            b"L"
            + _frame(str(link.ordinal).encode("ascii"))
            + _frame(link.kind.value.encode("ascii"))
            + _frame(_encode_ref(link.source))
            + _frame(_encode_ref(link.target))
            + _frame(b"" if link.witness_ref is None else _encode_ref(link.witness_ref))
            + _frame(_encode_fields(link.fields))
        )
        for link in inspection.links
    )
    states = b"".join(
        _frame(
            b"S"
            + _frame(str(state.ordinal).encode("ascii"))
            + _frame(state.kind.value.encode("ascii"))
            + _frame(_encode_ref(state.owner))
            + _frame(state.status.encode("utf-8"))
            + _frame(
                b""
                if state.reason is None
                else state.reason.encode("utf-8", "surrogatepass")
            )
            + _frame(_encode_fields(state.fields))
        )
        for state in inspection.states
    )
    return _FORMAT_MARKER + _frame(records) + _frame(links) + _frame(states)


def _encode_semantic_value(value: object) -> bytes:
    """Frame known semantic dataclasses without class names or Python repr."""

    if value is None:
        return b"n"
    if isinstance(value, StrEnum):
        return b"e" + _frame(value.value.encode("utf-8"))
    if type(value) is bool:
        return b"b1" if value else b"b0"
    if type(value) is int:
        return b"i" + str(value).encode("ascii")
    if type(value) is str:
        return b"s" + _frame(value.encode("utf-8", "surrogatepass"))
    if type(value) is bytes:
        return b"y" + _frame(value)
    if type(value) is tuple:
        return b"q" + b"".join(_frame(_encode_semantic_value(item)) for item in value)
    if is_dataclass(value):
        return b"d" + b"".join(
            _frame(item.name.encode("utf-8"))
            + _frame(_encode_semantic_value(getattr(value, item.name)))
            for item in dataclass_fields(value)  # pyright: ignore[reportArgumentType]
        )
    raise TypeError("Unsupported canonical semantic value.")
