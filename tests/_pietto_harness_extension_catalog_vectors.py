"""Static portable vectors for Phase 57 catalog pure boundaries."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from pietto._project.extension_catalog_inspection_pure_boundary import (
    EXTENSION_CATALOG_INSPECTION_PURE_ABSENT as IA,
    ExtensionCatalogInspectionPureDocument,
    ExtensionCatalogInspectionPureStatus,
    ExtensionCatalogInspectionPureTag,
    ExtensionCatalogInspectionPureValue,
    extension_catalog_inspection_pure_boolean as ib,
    extension_catalog_inspection_pure_enumeration as ie,
    extension_catalog_inspection_pure_integer as ii,
    extension_catalog_inspection_pure_text as is_,
    extension_catalog_inspection_pure_tuple as it,
)
from pietto.semantic.extension_catalog_pure_boundary import (
    EXTENSION_CATALOG_PURE_ABSENT as CA,
    ExtensionCatalogPureDocument,
    ExtensionCatalogPureStatus,
    ExtensionCatalogPureTag,
    ExtensionCatalogPureValue,
    encode_extension_catalog_pure_value,
    extension_catalog_pure_boolean as cb,
    extension_catalog_pure_enumeration as ce,
    extension_catalog_pure_integer as ci,
    extension_catalog_pure_record as cr,
    extension_catalog_pure_text as cs,
    extension_catalog_pure_tuple as ct,
)

EXTENSION_CATALOG_DIFFERENTIAL_VECTOR_FORMAT = (
    "pietto.extension-catalog-differential.v1"
)


class ExtensionCatalogDifferentialBoundary(StrEnum):
    CATALOG = "catalog"
    INSPECTION = "inspection"


class ExtensionCatalogDifferentialClassification(StrEnum):
    PORTABLE_EVALUATION = "portable_evaluation"
    PORTABLE_REJECTION = "portable_rejection"


type _Status = ExtensionCatalogPureStatus | ExtensionCatalogInspectionPureStatus
type _Document = ExtensionCatalogPureDocument | ExtensionCatalogInspectionPureDocument


@dataclass(frozen=True, slots=True)
class ExtensionCatalogDifferentialVector:
    vector_format: str
    vector_id: str
    boundary: ExtensionCatalogDifferentialBoundary
    classification: ExtensionCatalogDifferentialClassification
    purposes: tuple[str, ...]
    document: _Document
    expected_status: _Status
    expected_item_position: int | None
    expected_field_position: int | None
    expected_byte_length: int | None
    expected_sha256: str | None


def _catalog_reference(name: str = "synthetic") -> ExtensionCatalogPureValue:
    identity = cr(
        "ExtensionCatalogIdentity",
        ("namespace", cs("org.example.catalogs")),
        ("name", cs(name)),
    )
    return cr(
        "ExtensionCatalogReference",
        ("identity", identity),
        ("release", cs("1")),
    )


def _catalog_target(extension: str = "example_extension") -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogTarget",
        ("database_family", cs("PostgreSQL")),
        ("database_release", cs("18")),
        ("extension_identity", cs(extension)),
        ("extension_release", cs("1.0")),
    )


def _catalog_source(position: int) -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogSourceOccurrence",
        ("owner", _catalog_reference()),
        ("position", ci(position)),
        (
            "provenance",
            cr(
                "ExtensionCatalogSourceProvenance",
                ("source_authority", cs("example/upstream")),
                ("source_revision", cs(f"revision-{position}")),
                ("source_locator", cs(f"sql/source-{position}.sql")),
                ("curation", cs(f"curation-{position}")),
            ),
        ),
    )


def _catalog_metadata(source_count: int) -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogMetadata",
        (
            "schema_version",
            ce("ExtensionCatalogSchemaVersion", "pietto.extension-catalog.v1"),
        ),
        ("catalog", _catalog_reference()),
        ("target", _catalog_target()),
        (
            "source_occurrences",
            ct(*(_catalog_source(position) for position in range(source_count))),
        ),
    )


def _builtin_type(name: str = "text") -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogTypeReference",
        ("kind", ce("ExtensionCatalogTypeReferenceKind", "postgres_builtin")),
        ("logical_type", CA),
        ("physical_name", cs(name)),
        ("extension_identity", CA),
    )


def _native_type(name: str = "native") -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogTypeReference",
        ("kind", ce("ExtensionCatalogTypeReferenceKind", "extension_native")),
        ("logical_type", CA),
        ("physical_name", cs(name)),
        ("extension_identity", cs("example_extension")),
    )


def _logical_type() -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogTypeReference",
        ("kind", ce("ExtensionCatalogTypeReferenceKind", "pietto_logical")),
        (
            "logical_type",
            cr(
                "LogicalTypeIdentity",
                ("name", cs("Text")),
                ("kind", ce("TypeKind", "builtin")),
            ),
        ),
        ("physical_name", CA),
        ("extension_identity", CA),
    )


def _exact_type(reference: ExtensionCatalogPureValue) -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogDeclarationTypeUse",
        ("kind", ce("ExtensionCatalogDeclarationTypeUseKind", "exact")),
        ("exact_type", reference),
        ("source_spelling", CA),
        ("unmodeled_reasons", ct()),
    )


def _unmodeled_type(spelling: str = "text[]") -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogDeclarationTypeUse",
        ("kind", ce("ExtensionCatalogDeclarationTypeUseKind", "unmodeled")),
        ("exact_type", CA),
        ("source_spelling", cs(spelling)),
        (
            "unmodeled_reasons",
            ct(ce("ExtensionCatalogUnmodeledReason", "unsupported_type_form")),
        ),
    )


def _evidence(
    *source_positions: int,
    unmodeled: bool = False,
    exposure: str = "direct_sql_surface",
) -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogEntryEvidence",
        (
            "matchability",
            ce(
                "ExtensionCatalogMatchability",
                "cataloged_unmodeled" if unmodeled else "exact_matchable",
            ),
        ),
        ("exposure", ce("ExtensionCatalogExposure", exposure)),
        (
            "unmodeled_reasons",
            (
                ct(ce("ExtensionCatalogUnmodeledReason", "unsupported_type_form"))
                if unmodeled
                else ct()
            ),
        ),
        ("source_positions", ct(*(ci(position) for position in source_positions))),
    )


def _callable_identity(name: str = "shared") -> ExtensionCatalogPureValue:
    return cr(
        "PostgreSQLCallableIdentity",
        ("sql_name", cs(name)),
        ("input_types", ct(_builtin_type())),
    )


def _declaration(
    name: str = "shared",
    *,
    unmodeled: bool = False,
) -> ExtensionCatalogPureValue:
    return cr(
        "PostgreSQLCallableDeclaration",
        ("sql_name", cs(name)),
        (
            "input_types",
            ct(_unmodeled_type() if unmodeled else _exact_type(_builtin_type())),
        ),
        ("identity", CA if unmodeled else _callable_identity(name)),
    )


def _scalar_entry(
    source_position: int,
    *,
    result: str = "text",
    exposure: str = "direct_sql_surface",
) -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionScalarFunctionCatalogEntry",
        ("declaration", _declaration()),
        ("result_type", _exact_type(_builtin_type(result))),
        ("null_call_behavior", ce("PostgreSQLNullCallBehavior", "strict")),
        ("volatility", ce("PostgreSQLVolatility", "immutable")),
        ("parallel_safety", ce("PostgreSQLParallelSafety", "safe")),
        ("has_default_arguments", cb(False)),
        ("is_variadic", cb(False)),
        ("returns_set", cb(False)),
        ("has_polymorphic_or_pseudo_types", cb(False)),
        ("evidence", _evidence(source_position, exposure=exposure)),
    )


def _unmodeled_scalar_entry(source_position: int) -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionScalarFunctionCatalogEntry",
        ("declaration", _declaration("complex", unmodeled=True)),
        ("result_type", _exact_type(_builtin_type())),
        ("null_call_behavior", ce("PostgreSQLNullCallBehavior", "unknown")),
        ("volatility", ce("PostgreSQLVolatility", "unknown")),
        ("parallel_safety", ce("PostgreSQLParallelSafety", "unknown")),
        ("has_default_arguments", cb(False)),
        ("is_variadic", cb(False)),
        ("returns_set", cb(False)),
        ("has_polymorphic_or_pseudo_types", cb(False)),
        ("evidence", _evidence(source_position, unmodeled=True)),
    )


def _all_family_entries() -> tuple[ExtensionCatalogPureValue, ...]:
    native = cr(
        "ExtensionNativeTypeCatalogEntry",
        ("type_identity", _native_type()),
        ("logical_mapping", _logical_type()),
        ("evidence", _evidence(0)),
    )
    aggregate = cr(
        "ExtensionAggregateCatalogEntry",
        ("kind", ce("PostgreSQLAggregateKind", "ordinary")),
        ("declaration", _declaration("aggregate")),
        ("result_type", _exact_type(_builtin_type())),
        ("parallel_safety", ce("PostgreSQLParallelSafety", "safe")),
        ("has_direct_arguments", cb(False)),
        ("is_variadic", cb(False)),
        ("evidence", _evidence(0)),
    )
    operand = _exact_type(_native_type())
    operator = cr(
        "ExtensionOperatorCatalogEntry",
        ("operator_name", cs("<->")),
        ("arity", ce("PostgreSQLOperatorArity", "binary")),
        ("operand_types", ct(operand, operand)),
        (
            "identity",
            cr(
                "PostgreSQLOperatorIdentity",
                ("operator_name", cs("<->")),
                ("arity", ce("PostgreSQLOperatorArity", "binary")),
                ("operand_types", ct(_native_type(), _native_type())),
            ),
        ),
        ("result_type", _exact_type(_builtin_type("float8"))),
        ("evidence", _evidence(0)),
    )
    cast = cr(
        "ExtensionCastCatalogEntry",
        ("source_type", _exact_type(_builtin_type())),
        ("target_type", _exact_type(_native_type())),
        (
            "identity",
            cr(
                "PostgreSQLCastIdentity",
                ("source_type", _builtin_type()),
                ("target_type", _native_type()),
            ),
        ),
        ("context", ce("PostgreSQLCastContext", "explicit_only")),
        ("method", ce("PostgreSQLCastMethod", "function")),
        ("evidence", _evidence(0)),
    )
    entries = (
        aggregate,
        cast,
        native,
        operator,
        _scalar_entry(0),
        _unmodeled_scalar_entry(0),
    )
    family = {
        "ExtensionAggregateCatalogEntry": "aggregate",
        "ExtensionCastCatalogEntry": "cast",
        "ExtensionNativeTypeCatalogEntry": "native_type",
        "ExtensionOperatorCatalogEntry": "operator",
        "ExtensionScalarFunctionCatalogEntry": "scalar_function",
    }
    return tuple(
        sorted(
            entries,
            key=lambda entry: encode_extension_catalog_pure_value(
                ct(
                    ce("ExtensionCatalogEntryFamily", family[entry.record_kind or ""]),
                    entry,
                )
            ),
        )
    )


def _scope(name: str = "shared") -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogLookupScope",
        ("family", ce("ExtensionCatalogEntryFamily", "scalar_function")),
        ("identity", _callable_identity(name)),
    )


def _claim(kind: str, source_position: int) -> ExtensionCatalogPureValue:
    return cr(
        "ExtensionCatalogCompletenessClaim",
        ("scope", _scope("missing")),
        ("kind", ce("ExtensionCatalogCompletenessClaimKind", kind)),
        ("source_positions", ct(ci(source_position))),
    )


def _catalog_document(
    *,
    sources: int = 0,
    entries: tuple[ExtensionCatalogPureValue, ...] = (),
    groups: tuple[ExtensionCatalogPureValue, ...] = (),
    claims: tuple[ExtensionCatalogPureValue, ...] = (),
    completeness_groups: tuple[ExtensionCatalogPureValue, ...] = (),
) -> ExtensionCatalogPureDocument:
    return ExtensionCatalogPureDocument(
        root=ct(
            cs("extension_catalog"),
            _catalog_metadata(sources),
            ct(*entries),
            ct(*groups),
            ct(*claims),
            ct(*completeness_groups),
        )
    )


def _accepted_catalog_documents() -> tuple[
    tuple[str, tuple[str, ...], ExtensionCatalogPureDocument], ...
]:
    all_families = _catalog_document(sources=1, entries=_all_family_entries())
    first = _scalar_entry(0)
    second = _scalar_entry(1)
    duplicate_entries = tuple(
        sorted(
            (first, second),
            key=lambda entry: encode_extension_catalog_pure_value(
                ct(ce("ExtensionCatalogEntryFamily", "scalar_function"), entry)
            ),
        )
    )
    duplicate_group = cr(
        "ExtensionCatalogExactEntryGroup",
        ("scope", _scope()),
        ("state", ce("ExtensionCatalogExactEntryGroupState", "consistent_duplicate")),
        ("entries", ct(*duplicate_entries)),
    )
    complete = _claim("complete", 0)
    complete_group = cr(
        "ExtensionCatalogCompletenessGroup",
        ("scope", _scope("missing")),
        ("state", ce("ExtensionCatalogCompletenessState", "complete")),
        ("claims", ct(complete)),
    )
    duplicate = _catalog_document(
        sources=2,
        entries=duplicate_entries,
        groups=(duplicate_group,),
        claims=(complete,),
        completeness_groups=(complete_group,),
    )
    conflict_entries = tuple(
        sorted(
            (_scalar_entry(0), _scalar_entry(1, result="int4")),
            key=lambda entry: encode_extension_catalog_pure_value(
                ct(ce("ExtensionCatalogEntryFamily", "scalar_function"), entry)
            ),
        )
    )
    conflict_group = cr(
        "ExtensionCatalogExactEntryGroup",
        ("scope", _scope()),
        ("state", ce("ExtensionCatalogExactEntryGroupState", "evidence_conflict")),
        ("entries", ct(*conflict_entries)),
    )
    complete = _claim("complete", 0)
    incomplete = _claim("incomplete", 1)
    claims = tuple(
        sorted((complete, incomplete), key=encode_extension_catalog_pure_value)
    )
    completeness_conflict = cr(
        "ExtensionCatalogCompletenessGroup",
        ("scope", _scope("missing")),
        ("state", ce("ExtensionCatalogCompletenessState", "conflict")),
        ("claims", ct(*claims)),
    )
    conflict = _catalog_document(
        sources=2,
        entries=conflict_entries,
        groups=(conflict_group,),
        claims=claims,
        completeness_groups=(completeness_conflict,),
    )
    return (
        ("catalog_minimal", ("minimal_catalog",), _catalog_document()),
        (
            "catalog_all_families",
            ("all_five_entry_families", "structured_types", "unmodeled_type_use"),
            all_families,
        ),
        (
            "catalog_consistent_duplicate",
            ("consistent_duplicate", "complete_completeness", "ordered_evidence"),
            duplicate,
        ),
        (
            "catalog_evidence_conflict",
            ("evidence_conflict", "conflicting_completeness"),
            conflict,
        ),
    )


def _ireference(name: str = "synthetic") -> ExtensionCatalogInspectionPureValue:
    return it(is_("reference"), is_("org.example.catalogs"), is_(name), is_("1"))


def _itarget(
    extension: str = "example_extension",
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("target"),
        is_("PostgreSQL"),
        is_("18"),
        is_(extension),
        is_("1.0"),
    )


def _itype_reference(
    name: str = "text", *, native: bool = False
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("type_reference"),
        ie(
            "ExtensionCatalogTypeReferenceKind",
            "extension_native" if native else "postgres_builtin",
        ),
        IA,
        IA,
        is_(name),
        is_("example_extension") if native else IA,
    )


def _itype_use(
    name: str = "text",
    *,
    unmodeled: bool = False,
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("type_use"),
        ie(
            "ExtensionCatalogDeclarationTypeUseKind",
            "unmodeled" if unmodeled else "exact",
        ),
        IA if unmodeled else _itype_reference(name),
        is_(name) if unmodeled else IA,
        (
            it(ie("ExtensionCatalogUnmodeledReason", "unsupported_type_form"))
            if unmodeled
            else it()
        ),
    )


def _icallable_identity(name: str = "shared") -> ExtensionCatalogInspectionPureValue:
    return it(is_("callable_identity"), is_(name), it(_itype_reference()))


def _iscope(name: str = "shared") -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("scope"),
        ie("ExtensionCatalogEntryFamily", "scalar_function"),
        _icallable_identity(name),
    )


def _ideclaration(
    name: str = "shared",
    *,
    unmodeled: bool = False,
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("declaration"),
        is_(name),
        it(_itype_use("text[]", unmodeled=True) if unmodeled else _itype_use()),
        IA if unmodeled else _icallable_identity(name),
    )


def _ientry_evidence(
    *positions: int,
    unmodeled: bool = False,
    exposure: str = "direct_sql_surface",
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("entry_evidence"),
        ie(
            "ExtensionCatalogMatchability",
            "cataloged_unmodeled" if unmodeled else "exact_matchable",
        ),
        ie("ExtensionCatalogExposure", exposure),
        (
            it(ie("ExtensionCatalogUnmodeledReason", "unsupported_type_form"))
            if unmodeled
            else it()
        ),
        it(*(ii(position) for position in positions)),
    )


def _ientry(
    position: int,
    *,
    result: str = "text",
    unmodeled: bool = False,
    exposure: str = "direct_sql_surface",
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("scalar_function_entry"),
        ii(position),
        _ideclaration("complex" if unmodeled else "shared", unmodeled=unmodeled),
        _itype_use(result),
        ie("PostgreSQLNullCallBehavior", "unknown" if unmodeled else "strict"),
        ie("PostgreSQLVolatility", "unknown" if unmodeled else "immutable"),
        ie("PostgreSQLParallelSafety", "unknown" if unmodeled else "safe"),
        ib(False),
        ib(False),
        ib(False),
        ib(False),
        _ientry_evidence(position, unmodeled=unmodeled, exposure=exposure),
    )


def _isource(position: int) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("source"),
        ii(position),
        is_("example/upstream"),
        is_(f"revision-{position}"),
        is_(f"sql/source-{position}.sql"),
        is_(f"curation-{position}"),
    )


def _iclaim(position: int, kind: str) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("completeness_claim"),
        ii(position),
        _iscope("missing"),
        ie("ExtensionCatalogCompletenessClaimKind", kind),
        it(ii(position)),
    )


def _icatalog(
    position: int,
    *,
    name: str = "synthetic",
    entries: tuple[ExtensionCatalogInspectionPureValue, ...] = (),
    groups: tuple[ExtensionCatalogInspectionPureValue, ...] = (),
    claims: tuple[ExtensionCatalogInspectionPureValue, ...] = (),
    completeness_groups: tuple[ExtensionCatalogInspectionPureValue, ...] = (),
    sources: int = 1,
    digest_character: str = "a",
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("catalog"),
        ii(position),
        _ireference(name),
        _itarget(),
        is_(digest_character * 64),
        ii(100 + position),
        it(*(_isource(source) for source in range(sources))),
        it(*entries),
        it(*groups),
        it(*claims),
        it(*completeness_groups),
    )


def _ikey(subject: str = "synthetic") -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("key"),
        ie("CapabilityDomain", "extension_signature"),
        is_(subject),
        is_("exact signature"),
        it(is_("semantic")),
        is_("typed selector"),
        is_("postgresql"),
        is_("example_extension"),
    )


def _ievidence(position: int = 0) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("capability_evidence"),
        ie("CapabilityEvidenceSource", "semantic_catalog"),
        is_(f"sql/source-{position}.sql"),
        is_(f"member:{position}"),
        IA,
        is_("postgresql"),
        IA,
        is_("example_extension"),
    )


def _ifact(position: int = 0) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("fact"),
        _ikey(),
        ie("CapabilitySupport", "supported"),
        ie("CapabilityDispositionKind", "none"),
        IA,
        IA,
        it(_ievidence(position)),
    )


def _iavailability(
    position: int,
    *,
    owner: str = "compiler",
    project: str | None = None,
    catalog_position: int = 0,
    digest_character: str = "a",
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("availability"),
        ii(position),
        ie("ExtensionCatalogAvailabilityOwner", owner),
        IA if project is None else is_(project),
        ii(catalog_position),
        _ireference("synthetic" if catalog_position == 0 else "zz_second"),
        _itarget(),
        is_(digest_character * 64),
    )


def _icandidate(
    catalog_position: int,
    *declaration_positions: int,
    digest_character: str = "a",
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("candidate"),
        ii(catalog_position),
        _ireference("synthetic" if catalog_position == 0 else "zz_second"),
        _itarget(),
        is_(digest_character * 64),
        it(*(ii(position) for position in declaration_positions)),
    )


def _iselection(
    outcome: str,
    *,
    availability: tuple[ExtensionCatalogInspectionPureValue, ...],
    candidates: tuple[ExtensionCatalogInspectionPureValue, ...],
    active_project: str | None = None,
    applicable: tuple[int, ...] = (),
    excluded: tuple[int, ...] = (),
    target: tuple[int, ...] = (),
    selected: int | None = None,
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("selection"),
        _itarget(),
        IA if active_project is None else is_(active_project),
        ie("ExtensionCatalogSelectionOutcome", outcome),
        it(*availability),
        it(*(ii(position) for position in applicable)),
        it(*(ii(position) for position in excluded)),
        it(*(ii(position) for position in target)),
        it(*candidates),
        IA if selected is None else ii(selected),
    )


def _iprovider_inputs(
    *,
    facts: tuple[ExtensionCatalogInspectionPureValue, ...] = (),
    complete: bool = False,
    reason: str | None = None,
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("provider_inputs"),
        _ikey(),
        ib(complete),
        IA if reason is None else ie("CapabilityReasonCode", reason),
        it(*facts),
    )


def _ilookup(
    variant: str,
    *,
    reason: str | None = None,
    facts: tuple[ExtensionCatalogInspectionPureValue, ...] = (),
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("lookup"),
        ie("ExtensionCatalogInspectionLookupVariant", variant),
        IA if reason is None else ie("CapabilityReasonCode", reason),
        it(*facts),
    )


def _iprovider(
    *,
    selection: ExtensionCatalogInspectionPureValue,
    selected: int | None,
    exact_group: int | None = None,
    blockers: tuple[int, ...] = (),
    completeness: int | None = None,
    provider_inputs: ExtensionCatalogInspectionPureValue,
    lookup: ExtensionCatalogInspectionPureValue,
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("provider_occurrence"),
        ii(0),
        _ikey(),
        _iscope(),
        is_("PostgreSQL"),
        selection,
        IA if selected is None else ii(selected),
        IA if exact_group is None else ii(exact_group),
        it(*(ii(position) for position in blockers)),
        IA if completeness is None else ii(completeness),
        provider_inputs,
        lookup,
    )


def _inspection_document(
    catalogs: tuple[ExtensionCatalogInspectionPureValue, ...],
    providers: tuple[ExtensionCatalogInspectionPureValue, ...],
    *,
    name: str = "synthetic",
) -> ExtensionCatalogInspectionPureDocument:
    return ExtensionCatalogInspectionPureDocument(
        root=it(
            is_("extension_catalog_inspection"),
            ie(
                "ExtensionCatalogInspectionFormat",
                "pietto.extension-catalog-inspection.v1",
            ),
            is_("consumer"),
            is_(name),
            it(*catalogs),
            it(*providers),
        )
    )


def _iexact_group(
    position: int,
    state: str,
    *entry_positions: int,
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("exact_group"),
        ii(position),
        _iscope(),
        ie("ExtensionCatalogExactEntryGroupState", state),
        it(*(ii(item) for item in entry_positions)),
    )


def _icompleteness_group(
    position: int,
    state: str,
    *claim_positions: int,
) -> ExtensionCatalogInspectionPureValue:
    return it(
        is_("completeness_group"),
        ii(position),
        _iscope("missing"),
        ie("ExtensionCatalogCompletenessState", state),
        it(*(ii(item) for item in claim_positions)),
    )


def _accepted_inspection_documents() -> tuple[
    tuple[str, tuple[str, ...], ExtensionCatalogInspectionPureDocument], ...
]:
    exact_entry = _ientry(0)
    exact_group = _iexact_group(0, "unique", 0)
    found_catalog = _icatalog(
        0,
        entries=(exact_entry,),
        groups=(exact_group,),
    )
    second_catalog = _icatalog(
        1,
        name="zz_second",
        digest_character="b",
    )
    project_availability = (
        _iavailability(0),
        _iavailability(1, owner="project", project="projects/current"),
        _iavailability(2, owner="project", project="projects/foreign"),
    )
    found_selection = _iselection(
        "selected",
        availability=project_availability,
        candidates=(_icandidate(0, 0, 1),),
        active_project="projects/current",
        applicable=(0, 1),
        excluded=(2,),
        target=(0, 1),
        selected=0,
    )
    found_fact = _ifact()
    found_provider = _iprovider(
        selection=found_selection,
        selected=0,
        exact_group=0,
        provider_inputs=_iprovider_inputs(facts=(found_fact,)),
        lookup=_ilookup("found", facts=(found_fact,)),
    )
    found = _inspection_document(
        (found_catalog, second_catalog),
        (found_provider,),
        name="found",
    )

    complete_claim = _iclaim(0, "complete")
    complete_catalog = _icatalog(
        0,
        claims=(complete_claim,),
        completeness_groups=(_icompleteness_group(0, "complete", 0),),
    )
    selected = _iselection(
        "selected",
        availability=(_iavailability(0),),
        candidates=(_icandidate(0, 0),),
        applicable=(0,),
        target=(0,),
        selected=0,
    )
    absent = _inspection_document(
        (complete_catalog,),
        (
            _iprovider(
                selection=selected,
                selected=0,
                completeness=0,
                provider_inputs=_iprovider_inputs(complete=True),
                lookup=_ilookup("absent", reason="no_catalog_entry"),
            ),
        ),
        name="absent",
    )

    unmodeled_catalog = _icatalog(0, entries=(_ientry(0, unmodeled=True),))
    unknown_unmodeled = _inspection_document(
        (unmodeled_catalog,),
        (
            _iprovider(
                selection=selected,
                selected=0,
                blockers=(0,),
                provider_inputs=_iprovider_inputs(
                    reason="extension_cataloged_unmodeled"
                ),
                lookup=_ilookup(
                    "unknown",
                    reason="extension_cataloged_unmodeled",
                ),
            ),
        ),
        name="cataloged-unmodeled",
    )

    support_catalog = _icatalog(
        0,
        entries=(_ientry(0, exposure="implementation_support"),),
        groups=(exact_group,),
    )
    implementation_support = _inspection_document(
        (support_catalog,),
        (
            _iprovider(
                selection=selected,
                selected=0,
                exact_group=0,
                provider_inputs=_iprovider_inputs(
                    reason="extension_catalog_not_provider_eligible"
                ),
                lookup=_ilookup(
                    "unknown",
                    reason="extension_catalog_not_provider_eligible",
                ),
            ),
        ),
        name="implementation-support",
    )

    conflict_entries = (_ientry(0), _ientry(1, result="int4"))
    conflict_catalog = _icatalog(
        0,
        entries=conflict_entries,
        groups=(_iexact_group(0, "evidence_conflict", 0, 1),),
        sources=2,
    )
    first_fact = _ifact(0)
    second_fact = _ifact(1)
    evidence_conflict = _inspection_document(
        (conflict_catalog,),
        (
            _iprovider(
                selection=selected,
                selected=0,
                exact_group=0,
                provider_inputs=_iprovider_inputs(facts=(first_fact, second_fact)),
                lookup=_ilookup(
                    "conflict",
                    reason="conflicting_evidence",
                    facts=(first_fact, second_fact),
                ),
            ),
        ),
        name="evidence-conflict",
    )

    incomplete_claim = _iclaim(0, "incomplete")
    incomplete_catalog = _icatalog(
        0,
        claims=(incomplete_claim,),
        completeness_groups=(_icompleteness_group(0, "incomplete", 0),),
    )
    incomplete = _inspection_document(
        (incomplete_catalog,),
        (
            _iprovider(
                selection=selected,
                selected=0,
                completeness=0,
                provider_inputs=_iprovider_inputs(
                    reason="extension_catalog_completeness_incomplete"
                ),
                lookup=_ilookup(
                    "unknown",
                    reason="extension_catalog_completeness_incomplete",
                ),
            ),
        ),
        name="incomplete",
    )

    conflict_claims = (_iclaim(0, "complete"), _iclaim(1, "incomplete"))
    completeness_conflict_catalog = _icatalog(
        0,
        claims=conflict_claims,
        completeness_groups=(_icompleteness_group(0, "conflict", 0, 1),),
        sources=2,
    )
    completeness_conflict = _inspection_document(
        (completeness_conflict_catalog,),
        (
            _iprovider(
                selection=selected,
                selected=0,
                completeness=0,
                provider_inputs=_iprovider_inputs(
                    reason="extension_catalog_completeness_conflict"
                ),
                lookup=_ilookup(
                    "unknown",
                    reason="extension_catalog_completeness_conflict",
                ),
            ),
        ),
        name="completeness-conflict",
    )

    undeclared_selection = _iselection(
        "undeclared",
        availability=(),
        candidates=(),
    )
    undeclared = _inspection_document(
        (),
        (
            _iprovider(
                selection=undeclared_selection,
                selected=None,
                provider_inputs=_iprovider_inputs(
                    reason="extension_catalog_undeclared"
                ),
                lookup=_ilookup(
                    "unknown",
                    reason="extension_catalog_undeclared",
                ),
            ),
        ),
        name="undeclared",
    )

    multi_availability = (
        _iavailability(0),
        _iavailability(1, catalog_position=1, digest_character="b"),
    )
    ambiguous_selection = _iselection(
        "ambiguous",
        availability=multi_availability,
        candidates=(_icandidate(0, 0), _icandidate(1, 1, digest_character="b")),
        applicable=(0, 1),
        target=(0, 1),
    )
    ambiguous = _inspection_document(
        (found_catalog, second_catalog),
        (
            _iprovider(
                selection=ambiguous_selection,
                selected=None,
                provider_inputs=_iprovider_inputs(
                    reason="extension_catalog_selection_ambiguous"
                ),
                lookup=_ilookup(
                    "unknown",
                    reason="extension_catalog_selection_ambiguous",
                ),
            ),
        ),
        name="ambiguous",
    )
    assert ambiguous.root is not None
    ambiguous_root = ambiguous.root
    selection_conflict = replace(
        ambiguous,
        root=replace(
            ambiguous_root,
            items=(
                *ambiguous_root.items[:3],
                is_("selection-conflict"),
                ambiguous_root.items[4],
                it(
                    _iprovider(
                        selection=_iselection(
                            "conflict",
                            availability=multi_availability,
                            candidates=(
                                _icandidate(0, 0),
                                _icandidate(1, 1, digest_character="b"),
                            ),
                            applicable=(0, 1),
                            target=(0, 1),
                        ),
                        selected=None,
                        provider_inputs=_iprovider_inputs(
                            reason="extension_catalog_selection_conflict"
                        ),
                        lookup=_ilookup(
                            "unknown",
                            reason="extension_catalog_selection_conflict",
                        ),
                    )
                ),
            ),
        ),
    )
    return (
        (
            "inspection_found",
            (
                "selected_found",
                "multiple_catalogs",
                "compiler_project_excluded_provenance",
            ),
            found,
        ),
        ("inspection_absent", ("selected_absent", "completeness_complete"), absent),
        (
            "inspection_cataloged_unmodeled",
            ("selected_unknown", "cataloged_unmodeled"),
            unknown_unmodeled,
        ),
        (
            "inspection_implementation_support",
            ("implementation_support",),
            implementation_support,
        ),
        (
            "inspection_evidence_conflict",
            ("selected_capability_conflict", "exact_evidence_conflict"),
            evidence_conflict,
        ),
        (
            "inspection_completeness_incomplete",
            ("completeness_incomplete",),
            incomplete,
        ),
        (
            "inspection_completeness_conflict",
            ("completeness_conflict",),
            completeness_conflict,
        ),
        ("inspection_undeclared", ("selection_undeclared",), undeclared),
        ("inspection_ambiguous", ("selection_ambiguous",), ambiguous),
        (
            "inspection_selection_conflict",
            ("selection_conflict",),
            selection_conflict,
        ),
    )


def _creplace_field(
    record: ExtensionCatalogPureValue,
    key: str,
    value: ExtensionCatalogPureValue,
) -> ExtensionCatalogPureValue:
    return replace(
        record,
        fields=tuple(
            replace(field, value=value) if field.key == key else field
            for field in record.fields
        ),
    )


def _creplace_root_item(
    document: ExtensionCatalogPureDocument,
    position: int,
    value: ExtensionCatalogPureValue,
) -> ExtensionCatalogPureDocument:
    assert document.root is not None
    return replace(
        document,
        root=replace(
            document.root,
            items=tuple(
                value if index == position else item
                for index, item in enumerate(document.root.items)
            ),
        ),
    )


def _catalog_rejections() -> tuple[
    tuple[str, str, ExtensionCatalogPureDocument, ExtensionCatalogPureStatus], ...
]:
    minimal = _catalog_document()
    all_families = _accepted_catalog_documents()[1][2]
    duplicate = _accepted_catalog_documents()[2][2]
    conflict = _accepted_catalog_documents()[3][2]
    assert minimal.root is not None
    assert all_families.root is not None
    assert duplicate.root is not None
    assert conflict.root is not None

    metadata = minimal.root.items[1]
    invalid_format = _creplace_field(
        metadata,
        "schema_version",
        ce(
            "ExtensionCatalogSchemaVersion",
            "pietto.extension-catalog.invalid",
        ),
    )
    unknown_tag = ExtensionCatalogPureValue(tag=ExtensionCatalogPureTag.UNKNOWN)
    malformed_absent = ExtensionCatalogPureValue(
        tag=ExtensionCatalogPureTag.ABSENT,
        text="payload",
    )
    unknown_enum = ce("ExtensionCatalogSchemaVersion", "unknown")
    unknown_record = cr("UnknownRecord")

    source_metadata = all_families.root.items[1]
    sources = _field_value(source_metadata, "source_occurrences")
    source = sources.items[0]
    sparse_source = _creplace_field(source, "position", ci(2))
    sparse_sources = replace(sources, items=(sparse_source,))
    sparse_metadata = _creplace_field(
        source_metadata,
        "source_occurrences",
        sparse_sources,
    )

    entries = all_families.root.items[2]
    scalar_position = next(
        index
        for index, entry in enumerate(entries.items)
        if entry.record_kind == "ExtensionScalarFunctionCatalogEntry"
        and _field_value(entry, "declaration").fields[0].value.text == "shared"
    )
    scalar = entries.items[scalar_position]
    evidence = _field_value(scalar, "evidence")
    invalid_evidence = _creplace_field(evidence, "source_positions", ct(ci(1)))
    invalid_scalar = _creplace_field(scalar, "evidence", invalid_evidence)
    invalid_entries = replace(
        entries,
        items=tuple(
            invalid_scalar if index == scalar_position else entry
            for index, entry in enumerate(entries.items)
        ),
    )

    duplicate_groups = duplicate.root.items[3]
    duplicate_group = duplicate_groups.items[0]
    bad_scope = _creplace_field(
        _field_value(duplicate_group, "scope"),
        "family",
        ce("ExtensionCatalogEntryFamily", "native_type"),
    )
    family_group = _creplace_field(duplicate_group, "scope", bad_scope)
    wrong_state_group = _creplace_field(
        duplicate_group,
        "state",
        ce("ExtensionCatalogExactEntryGroupState", "unique"),
    )

    completeness_groups = conflict.root.items[5]
    completeness_group = completeness_groups.items[0]
    wrong_completeness = _creplace_field(
        completeness_group,
        "state",
        ce("ExtensionCatalogCompletenessState", "complete"),
    )

    return (
        (
            "catalog_reject_missing_root",
            "missing_root",
            ExtensionCatalogPureDocument(root=None),
            ExtensionCatalogPureStatus.MISSING_ROOT,
        ),
        (
            "catalog_reject_unknown_format",
            "unknown_format_marker",
            _creplace_root_item(minimal, 1, invalid_format),
            ExtensionCatalogPureStatus.UNKNOWN_FORMAT_MARKER,
        ),
        (
            "catalog_reject_unknown_tag",
            "unknown_value_tag",
            ExtensionCatalogPureDocument(root=ct(unknown_tag)),
            ExtensionCatalogPureStatus.UNKNOWN_VALUE_TAG,
        ),
        (
            "catalog_reject_value_shape",
            "value_shape_mismatch",
            ExtensionCatalogPureDocument(root=ct(malformed_absent)),
            ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH,
        ),
        (
            "catalog_reject_integer_range",
            "integer_out_of_range",
            ExtensionCatalogPureDocument(root=ct(ci(-1))),
            ExtensionCatalogPureStatus.INTEGER_OUT_OF_RANGE,
        ),
        (
            "catalog_reject_unknown_enum",
            "unknown_enumeration",
            ExtensionCatalogPureDocument(root=ct(unknown_enum)),
            ExtensionCatalogPureStatus.UNKNOWN_ENUMERATION,
        ),
        (
            "catalog_reject_record_schema",
            "record_schema_mismatch",
            ExtensionCatalogPureDocument(root=ct(unknown_record)),
            ExtensionCatalogPureStatus.RECORD_SCHEMA_MISMATCH,
        ),
        (
            "catalog_reject_missing_section",
            "missing_required_section",
            replace(minimal, root=replace(minimal.root, items=minimal.root.items[:-1])),
            ExtensionCatalogPureStatus.MISSING_REQUIRED_SECTION,
        ),
        (
            "catalog_reject_section_order",
            "section_order_violation",
            _creplace_root_item(minimal, 0, cs("wrong")),
            ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION,
        ),
        (
            "catalog_reject_ordinal",
            "ordinal_sequence_violation",
            _creplace_root_item(all_families, 1, sparse_metadata),
            ExtensionCatalogPureStatus.ORDINAL_SEQUENCE_VIOLATION,
        ),
        (
            "catalog_reject_child_count",
            "child_count_mismatch",
            _creplace_root_item(all_families, 2, invalid_entries),
            ExtensionCatalogPureStatus.CHILD_COUNT_MISMATCH,
        ),
        (
            "catalog_reject_family_identity",
            "inconsistent_family_identity",
            _creplace_root_item(
                duplicate, 3, replace(duplicate_groups, items=(family_group,))
            ),
            ExtensionCatalogPureStatus.INCONSISTENT_FAMILY_IDENTITY,
        ),
        (
            "catalog_reject_entry_group",
            "inconsistent_entry_group",
            _creplace_root_item(
                duplicate,
                3,
                replace(duplicate_groups, items=(wrong_state_group,)),
            ),
            ExtensionCatalogPureStatus.INCONSISTENT_ENTRY_GROUP,
        ),
        (
            "catalog_reject_completeness",
            "inconsistent_completeness_link",
            _creplace_root_item(
                conflict,
                5,
                replace(completeness_groups, items=(wrong_completeness,)),
            ),
            ExtensionCatalogPureStatus.INCONSISTENT_COMPLETENESS_LINK,
        ),
        (
            "catalog_reject_trailing",
            "trailing_item",
            replace(
                minimal, root=replace(minimal.root, items=(*minimal.root.items, ct()))
            ),
            ExtensionCatalogPureStatus.TRAILING_ITEM,
        ),
    )


def _field_value(
    record: ExtensionCatalogPureValue,
    key: str,
) -> ExtensionCatalogPureValue:
    return next(field.value for field in record.fields if field.key == key)


def _ireplace_root_item(
    document: ExtensionCatalogInspectionPureDocument,
    position: int,
    value: ExtensionCatalogInspectionPureValue,
) -> ExtensionCatalogInspectionPureDocument:
    assert document.root is not None
    return replace(
        document,
        root=replace(
            document.root,
            items=tuple(
                value if index == position else item
                for index, item in enumerate(document.root.items)
            ),
        ),
    )


def _inspection_rejections() -> tuple[
    tuple[
        str,
        str,
        ExtensionCatalogInspectionPureDocument,
        ExtensionCatalogInspectionPureStatus,
    ],
    ...,
]:
    accepted = _accepted_inspection_documents()
    found = accepted[0][2]
    evidence_conflict = accepted[4][2]
    completeness_conflict = accepted[6][2]
    assert found.root is not None
    assert evidence_conflict.root is not None
    assert completeness_conflict.root is not None
    catalogs = found.root.items[4]
    providers = found.root.items[5]
    provider = providers.items[0]
    catalog = catalogs.items[0]

    invalid_reference = replace(catalog.items[2], items=catalog.items[2].items[:-1])
    invalid_catalog = replace(
        catalog,
        items=(
            catalog.items[0],
            catalog.items[1],
            invalid_reference,
            *catalog.items[3:],
        ),
    )
    sparse_catalog = replace(
        catalog, items=(catalog.items[0], ii(2), *catalog.items[2:])
    )
    invalid_length_catalog = replace(
        catalog,
        items=(*catalog.items[:5], is_("not-integer"), *catalog.items[6:]),
    )
    invalid_sha_catalog = replace(
        catalog,
        items=(*catalog.items[:4], is_("bad"), *catalog.items[5:]),
    )
    bad_scope = replace(
        provider.items[3],
        items=(
            provider.items[3].items[0],
            ie("ExtensionCatalogEntryFamily", "native_type"),
            provider.items[3].items[2],
        ),
    )
    bad_family_provider = replace(
        provider,
        items=(*provider.items[:3], bad_scope, *provider.items[4:]),
    )

    conflict_catalogs = evidence_conflict.root.items[4]
    conflict_catalog = conflict_catalogs.items[0]
    conflict_groups = conflict_catalog.items[8]
    conflict_group = conflict_groups.items[0]
    wrong_group = replace(
        conflict_group,
        items=(
            *conflict_group.items[:3],
            ie("ExtensionCatalogExactEntryGroupState", "unique"),
            conflict_group.items[4],
        ),
    )
    bad_group_catalog = replace(
        conflict_catalog,
        items=(
            *conflict_catalog.items[:8],
            it(wrong_group),
            *conflict_catalog.items[9:],
        ),
    )

    completeness_catalogs = completeness_conflict.root.items[4]
    completeness_catalog = completeness_catalogs.items[0]
    completeness_groups = completeness_catalog.items[10]
    completeness_group = completeness_groups.items[0]
    wrong_completeness = replace(
        completeness_group,
        items=(
            *completeness_group.items[:3],
            ie("ExtensionCatalogCompletenessState", "complete"),
            completeness_group.items[4],
        ),
    )
    bad_completeness_catalog = replace(
        completeness_catalog,
        items=(*completeness_catalog.items[:10], it(wrong_completeness)),
    )

    selection = provider.items[5]
    bad_selection = replace(
        selection,
        items=(*selection.items[:8], it(), selection.items[9]),
    )
    bad_selection_provider = replace(
        provider,
        items=(*provider.items[:5], bad_selection, *provider.items[6:]),
    )
    candidate = selection.items[8].items[0]
    dangling_candidate = replace(
        candidate,
        items=(candidate.items[0], ii(99), *candidate.items[2:]),
    )
    dangling_selection = replace(
        selection,
        items=(*selection.items[:8], it(dangling_candidate), selection.items[9]),
    )
    dangling_provider = replace(
        provider,
        items=(*provider.items[:5], dangling_selection, *provider.items[6:]),
    )
    lookup = provider.items[11]
    bad_lookup = replace(
        lookup,
        items=(lookup.items[0], lookup.items[1], lookup.items[2], it()),
    )
    bad_lookup_provider = replace(
        provider,
        items=(*provider.items[:11], bad_lookup),
    )

    return (
        (
            "inspection_reject_missing_root",
            "missing_root",
            ExtensionCatalogInspectionPureDocument(root=None),
            ExtensionCatalogInspectionPureStatus.MISSING_ROOT,
        ),
        (
            "inspection_reject_unknown_format",
            "unknown_format_marker",
            _ireplace_root_item(
                found,
                1,
                ie(
                    "ExtensionCatalogInspectionFormat",
                    "pietto.extension-catalog-inspection.invalid",
                ),
            ),
            ExtensionCatalogInspectionPureStatus.UNKNOWN_FORMAT_MARKER,
        ),
        (
            "inspection_reject_unknown_tag",
            "unknown_value_tag",
            ExtensionCatalogInspectionPureDocument(
                root=it(
                    ExtensionCatalogInspectionPureValue(
                        tag=ExtensionCatalogInspectionPureTag.UNKNOWN
                    )
                )
            ),
            ExtensionCatalogInspectionPureStatus.UNKNOWN_VALUE_TAG,
        ),
        (
            "inspection_reject_value_shape",
            "value_shape_mismatch",
            ExtensionCatalogInspectionPureDocument(
                root=it(
                    ExtensionCatalogInspectionPureValue(
                        tag=ExtensionCatalogInspectionPureTag.ABSENT,
                        text="payload",
                    )
                )
            ),
            ExtensionCatalogInspectionPureStatus.VALUE_SHAPE_MISMATCH,
        ),
        (
            "inspection_reject_integer_range",
            "integer_out_of_range",
            ExtensionCatalogInspectionPureDocument(root=it(ii(-1))),
            ExtensionCatalogInspectionPureStatus.INTEGER_OUT_OF_RANGE,
        ),
        (
            "inspection_reject_unknown_enum",
            "unknown_enumeration",
            ExtensionCatalogInspectionPureDocument(
                root=it(ie("ExtensionCatalogInspectionFormat", "unknown"))
            ),
            ExtensionCatalogInspectionPureStatus.UNKNOWN_ENUMERATION,
        ),
        (
            "inspection_reject_tuple_schema",
            "tuple_schema_mismatch",
            _ireplace_root_item(
                found,
                4,
                replace(catalogs, items=(invalid_catalog, *catalogs.items[1:])),
            ),
            ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH,
        ),
        (
            "inspection_reject_section_order",
            "section_order_violation",
            _ireplace_root_item(found, 0, is_("wrong")),
            ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION,
        ),
        (
            "inspection_reject_ordinal",
            "ordinal_sequence_violation",
            _ireplace_root_item(
                found, 4, replace(catalogs, items=(sparse_catalog, *catalogs.items[1:]))
            ),
            ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION,
        ),
        (
            "inspection_reject_child_count",
            "child_count_mismatch",
            _ireplace_root_item(
                found,
                4,
                replace(catalogs, items=(invalid_length_catalog, *catalogs.items[1:])),
            ),
            ExtensionCatalogInspectionPureStatus.CHILD_COUNT_MISMATCH,
        ),
        (
            "inspection_reject_sha",
            "invalid_sha256",
            _ireplace_root_item(
                found,
                4,
                replace(catalogs, items=(invalid_sha_catalog, *catalogs.items[1:])),
            ),
            ExtensionCatalogInspectionPureStatus.INVALID_SHA256,
        ),
        (
            "inspection_reject_dangling",
            "dangling_positional_link",
            _ireplace_root_item(
                found, 5, replace(providers, items=(dangling_provider,))
            ),
            ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK,
        ),
        (
            "inspection_reject_family",
            "inconsistent_family_identity",
            _ireplace_root_item(
                found, 5, replace(providers, items=(bad_family_provider,))
            ),
            ExtensionCatalogInspectionPureStatus.INCONSISTENT_FAMILY_IDENTITY,
        ),
        (
            "inspection_reject_entry_group",
            "inconsistent_entry_group",
            _ireplace_root_item(
                evidence_conflict,
                4,
                replace(conflict_catalogs, items=(bad_group_catalog,)),
            ),
            ExtensionCatalogInspectionPureStatus.INCONSISTENT_ENTRY_GROUP,
        ),
        (
            "inspection_reject_completeness",
            "inconsistent_completeness_link",
            _ireplace_root_item(
                completeness_conflict,
                4,
                replace(completeness_catalogs, items=(bad_completeness_catalog,)),
            ),
            ExtensionCatalogInspectionPureStatus.INCONSISTENT_COMPLETENESS_LINK,
        ),
        (
            "inspection_reject_selection",
            "inconsistent_selection_link",
            _ireplace_root_item(
                found, 5, replace(providers, items=(bad_selection_provider,))
            ),
            ExtensionCatalogInspectionPureStatus.INCONSISTENT_SELECTION_LINK,
        ),
        (
            "inspection_reject_provider",
            "inconsistent_provider_result",
            _ireplace_root_item(
                found, 5, replace(providers, items=(bad_lookup_provider,))
            ),
            ExtensionCatalogInspectionPureStatus.INCONSISTENT_PROVIDER_RESULT,
        ),
        (
            "inspection_reject_trailing",
            "trailing_item",
            replace(found, root=replace(found.root, items=(*found.root.items, it()))),
            ExtensionCatalogInspectionPureStatus.TRAILING_ITEM,
        ),
    )


_EXPECTED_ACCEPTED_WITNESSES: dict[str, tuple[int, str]] = {
    "catalog_minimal": (
        820,
        "1b479f95659ae7bee94ee6954788174d04c632e507968b2b3ba980312b4f5359",
    ),
    "catalog_all_families": (
        13768,
        "4d357461eab34e2233ef64b8b0f6821f7d7b512a9d5c89bc2ecd174fcc4cd459",
    ),
    "catalog_consistent_duplicate": (
        14107,
        "11acee68fa155413a1c4e1f6ec62769881bf18135676523b8b7ae41e86c24518",
    ),
    "catalog_evidence_conflict": (
        15576,
        "d5c29ad13d6a92fc0a742b3b7dd8dfeec18f6c3b556e29be046b5eb4d8434d18",
    ),
    "inspection_found": (
        8860,
        "b382944b7d39882e3bd687b803b7a80a8aefd91f313e582f9c29a5e6f220b4a9",
    ),
    "inspection_absent": (
        4717,
        "98ea8eaa2ea995eda96f9defa0d2cd04e2258cfcaa58eb1720fc93d1ffb1ef45",
    ),
    "inspection_cataloged_unmodeled": (
        4972,
        "841b8e0566ce1e40a794113f2b3327216e08e7b39d2b62981e0cec887f31bda6",
    ),
    "inspection_implementation_support": (
        5756,
        "ecfa8be07b9f759739d57087f7157f98e0701ce9f4d6bb1f9fa9434661b302ea",
    ),
    "inspection_evidence_conflict": (
        10219,
        "d250ef8d3fc45030766f3532d110a3d543068d6e107a287c54543dfcee15a630",
    ),
    "inspection_completeness_incomplete": (
        4828,
        "15c901db4d747ce20e95d578ad0dea6caf4de6a8f9376a729d7c1aa304d192d9",
    ),
    "inspection_completeness_conflict": (
        5572,
        "dae689f8e8443bdc9bc7129f17de877630d34c0f6debb7e25703e03ac845ec58",
    ),
    "inspection_undeclared": (
        2025,
        "fc636c55c73a94528a7ea555381094de7d8c85736128e0b7809ac15f8d73a2c4",
    ),
    "inspection_ambiguous": (
        7375,
        "df099249e0c6630bac75c553b916c45668d84e61671bdc0f01e1ad0b5f541af3",
    ),
    "inspection_selection_conflict": (
        7381,
        "7670e5f731cf9d19f8bee03035806efe0a4718440a33ea312e9c4d44838d9d58",
    ),
}

_EXPECTED_REJECTION_COORDINATES: dict[str, tuple[int | None, int | None]] = {
    "catalog_reject_missing_root": (None, None),
    "catalog_reject_unknown_format": (0, None),
    "catalog_reject_unknown_tag": (1, None),
    "catalog_reject_value_shape": (1, None),
    "catalog_reject_integer_range": (1, None),
    "catalog_reject_unknown_enum": (1, None),
    "catalog_reject_record_schema": (1, None),
    "catalog_reject_missing_section": (0, None),
    "catalog_reject_section_order": (0, None),
    "catalog_reject_ordinal": (0, None),
    "catalog_reject_child_count": (0, None),
    "catalog_reject_family_identity": (0, None),
    "catalog_reject_entry_group": (0, None),
    "catalog_reject_completeness": (0, None),
    "catalog_reject_trailing": (0, None),
    "inspection_reject_missing_root": (None, None),
    "inspection_reject_unknown_format": (0, None),
    "inspection_reject_unknown_tag": (1, 0),
    "inspection_reject_value_shape": (1, 0),
    "inspection_reject_integer_range": (1, 0),
    "inspection_reject_unknown_enum": (1, 0),
    "inspection_reject_tuple_schema": (0, None),
    "inspection_reject_section_order": (0, None),
    "inspection_reject_ordinal": (0, None),
    "inspection_reject_child_count": (0, None),
    "inspection_reject_sha": (0, None),
    "inspection_reject_dangling": (0, None),
    "inspection_reject_family": (0, None),
    "inspection_reject_entry_group": (0, None),
    "inspection_reject_completeness": (0, None),
    "inspection_reject_selection": (0, None),
    "inspection_reject_provider": (0, None),
    "inspection_reject_trailing": (0, None),
}


def differential_vectors() -> tuple[ExtensionCatalogDifferentialVector, ...]:
    accepted: list[ExtensionCatalogDifferentialVector] = []
    for vector_id, purposes, document in _accepted_catalog_documents():
        length, sha256 = _EXPECTED_ACCEPTED_WITNESSES[vector_id]
        accepted.append(
            ExtensionCatalogDifferentialVector(
                EXTENSION_CATALOG_DIFFERENTIAL_VECTOR_FORMAT,
                vector_id,
                ExtensionCatalogDifferentialBoundary.CATALOG,
                ExtensionCatalogDifferentialClassification.PORTABLE_EVALUATION,
                purposes,
                document,
                ExtensionCatalogPureStatus.OK,
                None,
                None,
                length,
                sha256,
            )
        )
    for vector_id, purposes, document in _accepted_inspection_documents():
        length, sha256 = _EXPECTED_ACCEPTED_WITNESSES[vector_id]
        accepted.append(
            ExtensionCatalogDifferentialVector(
                EXTENSION_CATALOG_DIFFERENTIAL_VECTOR_FORMAT,
                vector_id,
                ExtensionCatalogDifferentialBoundary.INSPECTION,
                ExtensionCatalogDifferentialClassification.PORTABLE_EVALUATION,
                purposes,
                document,
                ExtensionCatalogInspectionPureStatus.OK,
                None,
                None,
                length,
                sha256,
            )
        )
    rejected: list[ExtensionCatalogDifferentialVector] = []
    for vector_id, purpose, document, status in _catalog_rejections():
        item, field = _EXPECTED_REJECTION_COORDINATES[vector_id]
        rejected.append(
            ExtensionCatalogDifferentialVector(
                EXTENSION_CATALOG_DIFFERENTIAL_VECTOR_FORMAT,
                vector_id,
                ExtensionCatalogDifferentialBoundary.CATALOG,
                ExtensionCatalogDifferentialClassification.PORTABLE_REJECTION,
                (purpose,),
                document,
                status,
                item,
                field,
                None,
                None,
            )
        )
    for vector_id, purpose, document, status in _inspection_rejections():
        item, field = _EXPECTED_REJECTION_COORDINATES[vector_id]
        rejected.append(
            ExtensionCatalogDifferentialVector(
                EXTENSION_CATALOG_DIFFERENTIAL_VECTOR_FORMAT,
                vector_id,
                ExtensionCatalogDifferentialBoundary.INSPECTION,
                ExtensionCatalogDifferentialClassification.PORTABLE_REJECTION,
                (purpose,),
                document,
                status,
                item,
                field,
                None,
                None,
            )
        )
    return tuple((*accepted, *rejected))
