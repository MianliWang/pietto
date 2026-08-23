"""Private pg_trgm 1.6 catalog for the exact PostgreSQL 18 target."""

from __future__ import annotations

from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryEvidence,
    ExtensionCatalogExposure,
    ExtensionCatalogIdentity,
    ExtensionCatalogMatchability,
    ExtensionCatalogMetadata,
    ExtensionCatalogReference,
    ExtensionCatalogSchemaVersion,
    ExtensionCatalogSourceOccurrence,
    ExtensionCatalogSourceProvenance,
    ExtensionCatalogTarget,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    ExtensionCatalogUnmodeledReason,
    ExtensionNativeTypeCatalogEntry,
    ExtensionOperatorCatalogEntry,
    ExtensionScalarFunctionCatalogEntry,
    PostgreSQLCallableDeclaration,
    PostgreSQLCallableIdentity,
    PostgreSQLNullCallBehavior,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
    PostgreSQLParallelSafety,
    PostgreSQLVolatility,
    _construct_extension_catalog,
)

__all__: tuple[str, ...] = ()

_SOURCE_REVISION = "724edf9bde9d356724ad384a2e196edc3c9f80f7"
_CATALOG_REFERENCE = ExtensionCatalogReference(
    ExtensionCatalogIdentity("pietto.postgresql", "pg_trgm"),
    "1",
)
_TARGET = ExtensionCatalogTarget("PostgreSQL", "18", "pg_trgm", "1.6")
_METADATA = ExtensionCatalogMetadata(
    ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
    _CATALOG_REFERENCE,
    _TARGET,
    tuple(
        ExtensionCatalogSourceOccurrence(
            _CATALOG_REFERENCE,
            position,
            ExtensionCatalogSourceProvenance(
                "github.com/postgres/postgres",
                _SOURCE_REVISION,
                locator,
                curation,
            ),
        )
        for position, (locator, curation) in enumerate(
            (
                (
                    "contrib/pg_trgm/pg_trgm.control",
                    "extension identity and release metadata",
                ),
                (
                    "doc/src/sgml/pgtrgm.sgml",
                    "documented user-facing functions and operators",
                ),
                (
                    "contrib/pg_trgm/pg_trgm--1.3.sql",
                    "base install declarations",
                ),
                (
                    "contrib/pg_trgm/pg_trgm--1.3--1.4.sql",
                    "1.4 effective-surface additions and modifications",
                ),
                (
                    "contrib/pg_trgm/pg_trgm--1.4--1.5.sql",
                    "1.5 effective-surface additions and modifications",
                ),
                (
                    "contrib/pg_trgm/pg_trgm--1.5--1.6.sql",
                    "1.6 effective-surface additions and modifications",
                ),
            )
        )
    ),
)


def _postgres_builtin(name: str) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.EXACT,
        exact_type=ExtensionCatalogTypeReference(
            ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
            physical_name=name,
        ),
    )


def _extension_native(name: str) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.EXACT,
        exact_type=ExtensionCatalogTypeReference(
            ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
            physical_name=name,
            extension_identity="pg_trgm",
        ),
    )


def _unmodeled(
    source_spelling: str,
    reason: ExtensionCatalogUnmodeledReason,
) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.UNMODELED,
        source_spelling=source_spelling,
        unmodeled_reasons=(reason,),
    )


def _exact_references(
    type_uses: tuple[ExtensionCatalogDeclarationTypeUse, ...],
) -> tuple[ExtensionCatalogTypeReference, ...] | None:
    if any(
        type_use.kind is ExtensionCatalogDeclarationTypeUseKind.UNMODELED
        for type_use in type_uses
    ):
        return None
    references: list[ExtensionCatalogTypeReference] = []
    for type_use in type_uses:
        assert type_use.exact_type is not None
        references.append(type_use.exact_type)
    return tuple(references)


def _reasons(
    *type_uses: ExtensionCatalogDeclarationTypeUse,
) -> tuple[ExtensionCatalogUnmodeledReason, ...]:
    return tuple(
        dict.fromkeys(
            reason for type_use in type_uses for reason in type_use.unmodeled_reasons
        )
    )


def _evidence(
    exposure: ExtensionCatalogExposure,
    reasons: tuple[ExtensionCatalogUnmodeledReason, ...] = (),
    *,
    source_positions: tuple[int, ...],
) -> ExtensionCatalogEntryEvidence:
    return ExtensionCatalogEntryEvidence(
        (
            ExtensionCatalogMatchability.CATALOGED_UNMODELED
            if reasons
            else ExtensionCatalogMatchability.EXACT_MATCHABLE
        ),
        exposure,
        reasons,
        source_positions,
    )


def _function(
    name: str,
    inputs: tuple[ExtensionCatalogDeclarationTypeUse, ...],
    result: ExtensionCatalogDeclarationTypeUse,
    exposure: ExtensionCatalogExposure,
    source_positions: tuple[int, ...],
    *,
    null_call: PostgreSQLNullCallBehavior = PostgreSQLNullCallBehavior.STRICT,
    volatility: PostgreSQLVolatility = PostgreSQLVolatility.IMMUTABLE,
    parallel: PostgreSQLParallelSafety = PostgreSQLParallelSafety.SAFE,
) -> ExtensionScalarFunctionCatalogEntry:
    references = _exact_references(inputs)
    reasons = _reasons(*inputs, result)
    return ExtensionScalarFunctionCatalogEntry(
        PostgreSQLCallableDeclaration(
            name,
            inputs,
            (
                None
                if references is None
                else PostgreSQLCallableIdentity(name, references)
            ),
        ),
        result,
        null_call,
        volatility,
        parallel,
        False,
        False,
        False,
        ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE in reasons,
        _evidence(exposure, reasons, source_positions=source_positions),
    )


def _direct_function(
    name: str,
    inputs: tuple[ExtensionCatalogDeclarationTypeUse, ...],
    result: ExtensionCatalogDeclarationTypeUse,
    source_position: int,
    *,
    null_call: PostgreSQLNullCallBehavior = PostgreSQLNullCallBehavior.STRICT,
    volatility: PostgreSQLVolatility = PostgreSQLVolatility.IMMUTABLE,
    parallel: PostgreSQLParallelSafety = PostgreSQLParallelSafety.SAFE,
) -> ExtensionScalarFunctionCatalogEntry:
    return _function(
        name,
        inputs,
        result,
        ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
        (1, source_position),
        null_call=null_call,
        volatility=volatility,
        parallel=parallel,
    )


def _support_function(
    name: str,
    inputs: tuple[ExtensionCatalogDeclarationTypeUse, ...],
    result: ExtensionCatalogDeclarationTypeUse,
    source_position: int,
    *,
    null_call: PostgreSQLNullCallBehavior = PostgreSQLNullCallBehavior.STRICT,
    volatility: PostgreSQLVolatility = PostgreSQLVolatility.IMMUTABLE,
    parallel: PostgreSQLParallelSafety = PostgreSQLParallelSafety.SAFE,
) -> ExtensionScalarFunctionCatalogEntry:
    return _function(
        name,
        inputs,
        result,
        ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT,
        (source_position,),
        null_call=null_call,
        volatility=volatility,
        parallel=parallel,
    )


def _operator(
    name: str,
    result: ExtensionCatalogDeclarationTypeUse,
    source_position: int,
) -> ExtensionOperatorCatalogEntry:
    assert _TEXT.exact_type is not None
    references = (_TEXT.exact_type, _TEXT.exact_type)
    return ExtensionOperatorCatalogEntry(
        name,
        PostgreSQLOperatorArity.BINARY,
        (_TEXT, _TEXT),
        PostgreSQLOperatorIdentity(
            name,
            PostgreSQLOperatorArity.BINARY,
            references,
        ),
        result,
        _evidence(
            ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
            source_positions=(1, source_position),
        ),
    )


_GTRGM = _extension_native("gtrgm")
_TEXT = _postgres_builtin("text")
_FLOAT4 = _postgres_builtin("float4")
_FLOAT8 = _postgres_builtin("float8")
_BOOL = _postgres_builtin("bool")
_SMALLINT = _postgres_builtin("smallint")
_OID = _postgres_builtin("oid")
_INT2 = _postgres_builtin("int2")
_INT4 = _postgres_builtin("int4")
_CHAR = _postgres_builtin('"char"')

_PSEUDO = ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE
_UNSUPPORTED_FORM = ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM
_CSTRING = _unmodeled("cstring", _PSEUDO)
_INTERNAL = _unmodeled("internal", _PSEUDO)
_VOID = _unmodeled("void", _PSEUDO)
_TEXT_ARRAY = _unmodeled("_text", _UNSUPPORTED_FORM)

assert _GTRGM.exact_type is not None
_NATIVE_TYPE_ENTRIES = (
    ExtensionNativeTypeCatalogEntry(
        _GTRGM.exact_type,
        None,
        _evidence(
            ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT,
            source_positions=(2,),
        ),
    ),
)

_BASE_FUNCTIONS = (
    _direct_function(
        "set_limit",
        (_FLOAT4,),
        _FLOAT4,
        2,
        volatility=PostgreSQLVolatility.VOLATILE,
        parallel=PostgreSQLParallelSafety.UNSAFE,
    ),
    _direct_function(
        "show_limit",
        (),
        _FLOAT4,
        2,
        volatility=PostgreSQLVolatility.STABLE,
    ),
    _direct_function("show_trgm", (_TEXT,), _TEXT_ARRAY, 2),
    _direct_function("similarity", (_TEXT, _TEXT), _FLOAT4, 2),
    _support_function(
        "similarity_op",
        (_TEXT, _TEXT),
        _BOOL,
        2,
        volatility=PostgreSQLVolatility.STABLE,
    ),
    _direct_function("word_similarity", (_TEXT, _TEXT), _FLOAT4, 2),
    _support_function(
        "word_similarity_op",
        (_TEXT, _TEXT),
        _BOOL,
        2,
        volatility=PostgreSQLVolatility.STABLE,
    ),
    _support_function(
        "word_similarity_commutator_op",
        (_TEXT, _TEXT),
        _BOOL,
        2,
        volatility=PostgreSQLVolatility.STABLE,
    ),
    _support_function("similarity_dist", (_TEXT, _TEXT), _FLOAT4, 2),
    _support_function("word_similarity_dist_op", (_TEXT, _TEXT), _FLOAT4, 2),
    _support_function(
        "word_similarity_dist_commutator_op",
        (_TEXT, _TEXT),
        _FLOAT4,
        2,
    ),
    _support_function("gtrgm_in", (_CSTRING,), _GTRGM, 2),
    _support_function("gtrgm_out", (_GTRGM,), _CSTRING, 2),
    _support_function(
        "gtrgm_consistent",
        (_INTERNAL, _TEXT, _SMALLINT, _OID, _INTERNAL),
        _BOOL,
        2,
    ),
    _support_function(
        "gtrgm_distance",
        (_INTERNAL, _TEXT, _SMALLINT, _OID, _INTERNAL),
        _FLOAT8,
        2,
    ),
    _support_function("gtrgm_compress", (_INTERNAL,), _INTERNAL, 2),
    _support_function("gtrgm_decompress", (_INTERNAL,), _INTERNAL, 2),
    _support_function(
        "gtrgm_penalty",
        (_INTERNAL, _INTERNAL, _INTERNAL),
        _INTERNAL,
        2,
    ),
    _support_function(
        "gtrgm_picksplit",
        (_INTERNAL, _INTERNAL),
        _INTERNAL,
        2,
    ),
    _support_function("gtrgm_union", (_INTERNAL, _INTERNAL), _GTRGM, 2),
    _support_function(
        "gtrgm_same",
        (_GTRGM, _GTRGM, _INTERNAL),
        _INTERNAL,
        2,
    ),
    _support_function(
        "gin_extract_value_trgm",
        (_TEXT, _INTERNAL),
        _INTERNAL,
        2,
    ),
    _support_function(
        "gin_extract_query_trgm",
        (_TEXT, _INTERNAL, _INT2, _INTERNAL, _INTERNAL, _INTERNAL, _INTERNAL),
        _INTERNAL,
        2,
    ),
    _support_function(
        "gin_trgm_consistent",
        (_INTERNAL, _INT2, _TEXT, _INT4, _INTERNAL, _INTERNAL, _INTERNAL, _INTERNAL),
        _BOOL,
        2,
    ),
    _support_function(
        "gin_trgm_triconsistent",
        (_INTERNAL, _INT2, _TEXT, _INT4, _INTERNAL, _INTERNAL, _INTERNAL),
        _CHAR,
        2,
    ),
)

_V14_FUNCTIONS = (
    _direct_function("strict_word_similarity", (_TEXT, _TEXT), _FLOAT4, 3),
    _support_function(
        "strict_word_similarity_op",
        (_TEXT, _TEXT),
        _BOOL,
        3,
        volatility=PostgreSQLVolatility.STABLE,
    ),
    _support_function(
        "strict_word_similarity_commutator_op",
        (_TEXT, _TEXT),
        _BOOL,
        3,
        volatility=PostgreSQLVolatility.STABLE,
    ),
    _support_function(
        "strict_word_similarity_dist_op",
        (_TEXT, _TEXT),
        _FLOAT4,
        3,
    ),
    _support_function(
        "strict_word_similarity_dist_commutator_op",
        (_TEXT, _TEXT),
        _FLOAT4,
        3,
    ),
)

_V15_FUNCTIONS = (
    _support_function(
        "gtrgm_options",
        (_INTERNAL,),
        _VOID,
        4,
        null_call=PostgreSQLNullCallBehavior.UNKNOWN,
    ),
)

_FUNCTION_ENTRIES = (*_BASE_FUNCTIONS, *_V14_FUNCTIONS, *_V15_FUNCTIONS)

_OPERATOR_ENTRIES = (
    _operator("%", _BOOL, 2),
    _operator("<%", _BOOL, 2),
    _operator("%>", _BOOL, 2),
    _operator("<->", _FLOAT4, 2),
    _operator("<<->", _FLOAT4, 2),
    _operator("<->>", _FLOAT4, 2),
    _operator("<<%", _BOOL, 3),
    _operator("%>>", _BOOL, 3),
    _operator("<<<->", _FLOAT4, 3),
    _operator("<->>>", _FLOAT4, 3),
)

_ENTRIES = (*_NATIVE_TYPE_ENTRIES, *_FUNCTION_ENTRIES, *_OPERATOR_ENTRIES)


def _build_pg_trgm_catalog() -> ConstructedExtensionCatalog:
    result = _construct_extension_catalog(_METADATA, _ENTRIES, ())
    if result.catalog is None:
        raise AssertionError("pg_trgm catalog construction must succeed")
    return result.catalog


PG_TRGM_V16_POSTGRESQL18_CATALOG = _build_pg_trgm_catalog()
