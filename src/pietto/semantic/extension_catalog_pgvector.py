"""Private pgvector 0.8.6 catalog for the exact PostgreSQL 18 target."""

from __future__ import annotations

from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
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
    PostgreSQLAggregateKind,
    PostgreSQLCallableDeclaration,
    PostgreSQLCallableIdentity,
    PostgreSQLCastContext,
    PostgreSQLCastIdentity,
    PostgreSQLCastMethod,
    PostgreSQLNullCallBehavior,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
    PostgreSQLParallelSafety,
    PostgreSQLVolatility,
    _construct_extension_catalog,
)

__all__: tuple[str, ...] = ()

_SOURCE_REVISION = "8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c"
_CATALOG_REFERENCE = ExtensionCatalogReference(
    ExtensionCatalogIdentity("pietto.postgresql", "pgvector"),
    "1",
)
_TARGET = ExtensionCatalogTarget("PostgreSQL", "18", "vector", "0.8.6")
_METADATA = ExtensionCatalogMetadata(
    ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
    _CATALOG_REFERENCE,
    _TARGET,
    tuple(
        ExtensionCatalogSourceOccurrence(
            _CATALOG_REFERENCE,
            position,
            ExtensionCatalogSourceProvenance(
                "github.com/pgvector/pgvector",
                _SOURCE_REVISION,
                locator,
                curation,
            ),
        )
        for position, (locator, curation) in enumerate(
            (
                ("vector.control", "extension identity and release metadata"),
                ("CHANGELOG.md", "release history"),
                (
                    "README.md",
                    "PostgreSQL support and user-facing surface",
                ),
                ("sql/vector.sql", "extension SQL declarations"),
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
            extension_identity="vector",
        ),
    )


def _unmodeled(
    source_spelling: str,
    *reasons: ExtensionCatalogUnmodeledReason,
) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.UNMODELED,
        source_spelling=source_spelling,
        unmodeled_reasons=reasons,
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
    source_positions: tuple[int, ...] = (3,),
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
    *,
    source_positions: tuple[int, ...],
    metadata_known: bool = True,
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
        (
            PostgreSQLNullCallBehavior.STRICT
            if metadata_known
            else PostgreSQLNullCallBehavior.UNKNOWN
        ),
        (
            PostgreSQLVolatility.IMMUTABLE
            if metadata_known
            else PostgreSQLVolatility.UNKNOWN
        ),
        (
            PostgreSQLParallelSafety.SAFE
            if metadata_known
            else PostgreSQLParallelSafety.UNKNOWN
        ),
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
) -> ExtensionScalarFunctionCatalogEntry:
    return _function(
        name,
        inputs,
        result,
        ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
        source_positions=(2, 3),
    )


def _support_function(
    name: str,
    inputs: tuple[ExtensionCatalogDeclarationTypeUse, ...],
    result: ExtensionCatalogDeclarationTypeUse,
    *,
    metadata_known: bool = True,
) -> ExtensionScalarFunctionCatalogEntry:
    return _function(
        name,
        inputs,
        result,
        ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT,
        source_positions=(3,),
        metadata_known=metadata_known,
    )


def _native_entry(
    type_use: ExtensionCatalogDeclarationTypeUse,
) -> ExtensionNativeTypeCatalogEntry:
    assert type_use.exact_type is not None
    return ExtensionNativeTypeCatalogEntry(
        type_use.exact_type,
        None,
        _evidence(
            ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
            source_positions=(2, 3),
        ),
    )


def _aggregate(
    name: str,
    input_type: ExtensionCatalogDeclarationTypeUse,
    result_type: ExtensionCatalogDeclarationTypeUse,
) -> ExtensionAggregateCatalogEntry:
    input_reference = _exact_references((input_type,))
    assert input_reference is not None
    return ExtensionAggregateCatalogEntry(
        PostgreSQLAggregateKind.ORDINARY,
        PostgreSQLCallableDeclaration(
            name,
            (input_type,),
            PostgreSQLCallableIdentity(name, input_reference),
        ),
        result_type,
        PostgreSQLParallelSafety.SAFE,
        False,
        False,
        _evidence(
            ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
            source_positions=(2, 3),
        ),
    )


def _operator(
    name: str,
    operand_type: ExtensionCatalogDeclarationTypeUse,
    result_type: ExtensionCatalogDeclarationTypeUse,
) -> ExtensionOperatorCatalogEntry:
    references = _exact_references((operand_type, operand_type))
    assert references is not None
    return ExtensionOperatorCatalogEntry(
        name,
        PostgreSQLOperatorArity.BINARY,
        (operand_type, operand_type),
        PostgreSQLOperatorIdentity(
            name,
            PostgreSQLOperatorArity.BINARY,
            references,
        ),
        result_type,
        _evidence(ExtensionCatalogExposure.DIRECT_SQL_SURFACE),
    )


def _cast(
    source_type: ExtensionCatalogDeclarationTypeUse,
    target_type: ExtensionCatalogDeclarationTypeUse,
    context: PostgreSQLCastContext,
) -> ExtensionCastCatalogEntry:
    references = _exact_references((source_type, target_type))
    reasons = _reasons(source_type, target_type)
    return ExtensionCastCatalogEntry(
        source_type,
        target_type,
        (
            None
            if references is None
            else PostgreSQLCastIdentity(references[0], references[1])
        ),
        context,
        PostgreSQLCastMethod.FUNCTION,
        _evidence(ExtensionCatalogExposure.DIRECT_SQL_SURFACE, reasons),
    )


_VECTOR = _extension_native("vector")
_HALFVEC = _extension_native("halfvec")
_SPARSEVEC = _extension_native("sparsevec")

_BIT = _postgres_builtin("bit")
_BOOL = _postgres_builtin("bool")
_BOOLEAN = _postgres_builtin("boolean")
_BYTEA = _postgres_builtin("bytea")
_FLOAT8 = _postgres_builtin("float8")
_INT = _postgres_builtin("int")
_INT4 = _postgres_builtin("int4")
_INTEGER = _postgres_builtin("integer")
_OID = _postgres_builtin("oid")

_UNSUPPORTED_TYPE_FORM = ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM
_PSEUDO_TYPE = ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE
_CSTRING = _unmodeled("cstring", _PSEUDO_TYPE)
_CSTRING_ARRAY = _unmodeled(
    "cstring[]",
    _UNSUPPORTED_TYPE_FORM,
    _PSEUDO_TYPE,
)
_INTERNAL = _unmodeled("internal", _PSEUDO_TYPE)
_INDEX_AM_HANDLER = _unmodeled("index_am_handler", _PSEUDO_TYPE)
_INTEGER_ARRAY = _unmodeled("integer[]", _UNSUPPORTED_TYPE_FORM)
_REAL_ARRAY = _unmodeled("real[]", _UNSUPPORTED_TYPE_FORM)
_DOUBLE_PRECISION_ARRAY = _unmodeled(
    "double precision[]",
    _UNSUPPORTED_TYPE_FORM,
)
_NUMERIC_ARRAY = _unmodeled("numeric[]", _UNSUPPORTED_TYPE_FORM)

_NATIVE_TYPE_ENTRIES = (
    _native_entry(_VECTOR),
    _native_entry(_HALFVEC),
    _native_entry(_SPARSEVEC),
)

_VECTOR_TYPE_FUNCTIONS = (
    _support_function("vector_in", (_CSTRING, _OID, _INTEGER), _VECTOR),
    _support_function("vector_out", (_VECTOR,), _CSTRING),
    _support_function("vector_typmod_in", (_CSTRING_ARRAY,), _INTEGER),
    _support_function("vector_recv", (_INTERNAL, _OID, _INTEGER), _VECTOR),
    _support_function("vector_send", (_VECTOR,), _BYTEA),
)
_VECTOR_DIRECT_FUNCTIONS = (
    _direct_function("l2_distance", (_VECTOR, _VECTOR), _FLOAT8),
    _direct_function("inner_product", (_VECTOR, _VECTOR), _FLOAT8),
    _direct_function("cosine_distance", (_VECTOR, _VECTOR), _FLOAT8),
    _direct_function("l1_distance", (_VECTOR, _VECTOR), _FLOAT8),
    _direct_function("vector_dims", (_VECTOR,), _INTEGER),
    _direct_function("vector_norm", (_VECTOR,), _FLOAT8),
    _direct_function("l2_normalize", (_VECTOR,), _VECTOR),
    _direct_function("binary_quantize", (_VECTOR,), _BIT),
    _direct_function("subvector", (_VECTOR, _INT, _INT), _VECTOR),
)
_VECTOR_PRIVATE_FUNCTIONS = (
    _support_function("vector_add", (_VECTOR, _VECTOR), _VECTOR),
    _support_function("vector_sub", (_VECTOR, _VECTOR), _VECTOR),
    _support_function("vector_mul", (_VECTOR, _VECTOR), _VECTOR),
    _support_function("vector_concat", (_VECTOR, _VECTOR), _VECTOR),
    _support_function("vector_lt", (_VECTOR, _VECTOR), _BOOL),
    _support_function("vector_le", (_VECTOR, _VECTOR), _BOOL),
    _support_function("vector_eq", (_VECTOR, _VECTOR), _BOOL),
    _support_function("vector_ne", (_VECTOR, _VECTOR), _BOOL),
    _support_function("vector_ge", (_VECTOR, _VECTOR), _BOOL),
    _support_function("vector_gt", (_VECTOR, _VECTOR), _BOOL),
    _support_function("vector_cmp", (_VECTOR, _VECTOR), _INT4),
    _support_function("vector_l2_squared_distance", (_VECTOR, _VECTOR), _FLOAT8),
    _support_function(
        "vector_negative_inner_product",
        (_VECTOR, _VECTOR),
        _FLOAT8,
    ),
    _support_function("vector_spherical_distance", (_VECTOR, _VECTOR), _FLOAT8),
    _support_function(
        "vector_accum",
        (_DOUBLE_PRECISION_ARRAY, _VECTOR),
        _DOUBLE_PRECISION_ARRAY,
    ),
    _support_function("vector_avg", (_DOUBLE_PRECISION_ARRAY,), _VECTOR),
    _support_function(
        "vector_combine",
        (_DOUBLE_PRECISION_ARRAY, _DOUBLE_PRECISION_ARRAY),
        _DOUBLE_PRECISION_ARRAY,
    ),
)
_VECTOR_CAST_FUNCTIONS = (
    _support_function("vector", (_VECTOR, _INTEGER, _BOOLEAN), _VECTOR),
    _support_function(
        "array_to_vector",
        (_INTEGER_ARRAY, _INTEGER, _BOOLEAN),
        _VECTOR,
    ),
    _support_function(
        "array_to_vector",
        (_REAL_ARRAY, _INTEGER, _BOOLEAN),
        _VECTOR,
    ),
    _support_function(
        "array_to_vector",
        (_DOUBLE_PRECISION_ARRAY, _INTEGER, _BOOLEAN),
        _VECTOR,
    ),
    _support_function(
        "array_to_vector",
        (_NUMERIC_ARRAY, _INTEGER, _BOOLEAN),
        _VECTOR,
    ),
    _support_function(
        "vector_to_float4",
        (_VECTOR, _INTEGER, _BOOLEAN),
        _REAL_ARRAY,
    ),
)

_ACCESS_METHOD_FUNCTIONS = (
    _support_function(
        "ivfflathandler",
        (_INTERNAL,),
        _INDEX_AM_HANDLER,
        metadata_known=False,
    ),
    _support_function(
        "hnswhandler",
        (_INTERNAL,),
        _INDEX_AM_HANDLER,
        metadata_known=False,
    ),
    _support_function(
        "ivfflat_halfvec_support",
        (_INTERNAL,),
        _INTERNAL,
        metadata_known=False,
    ),
    _support_function(
        "ivfflat_bit_support",
        (_INTERNAL,),
        _INTERNAL,
        metadata_known=False,
    ),
    _support_function(
        "hnsw_halfvec_support",
        (_INTERNAL,),
        _INTERNAL,
        metadata_known=False,
    ),
    _support_function(
        "hnsw_bit_support",
        (_INTERNAL,),
        _INTERNAL,
        metadata_known=False,
    ),
    _support_function(
        "hnsw_sparsevec_support",
        (_INTERNAL,),
        _INTERNAL,
        metadata_known=False,
    ),
)

_HALFVEC_TYPE_FUNCTIONS = (
    _support_function("halfvec_in", (_CSTRING, _OID, _INTEGER), _HALFVEC),
    _support_function("halfvec_out", (_HALFVEC,), _CSTRING),
    _support_function("halfvec_typmod_in", (_CSTRING_ARRAY,), _INTEGER),
    _support_function("halfvec_recv", (_INTERNAL, _OID, _INTEGER), _HALFVEC),
    _support_function("halfvec_send", (_HALFVEC,), _BYTEA),
)
_HALFVEC_DIRECT_FUNCTIONS = (
    _direct_function("l2_distance", (_HALFVEC, _HALFVEC), _FLOAT8),
    _direct_function("inner_product", (_HALFVEC, _HALFVEC), _FLOAT8),
    _direct_function("cosine_distance", (_HALFVEC, _HALFVEC), _FLOAT8),
    _direct_function("l1_distance", (_HALFVEC, _HALFVEC), _FLOAT8),
    _direct_function("vector_dims", (_HALFVEC,), _INTEGER),
    _direct_function("l2_norm", (_HALFVEC,), _FLOAT8),
    _direct_function("l2_normalize", (_HALFVEC,), _HALFVEC),
    _direct_function("binary_quantize", (_HALFVEC,), _BIT),
    _direct_function("subvector", (_HALFVEC, _INT, _INT), _HALFVEC),
)
_HALFVEC_PRIVATE_FUNCTIONS = (
    _support_function("halfvec_add", (_HALFVEC, _HALFVEC), _HALFVEC),
    _support_function("halfvec_sub", (_HALFVEC, _HALFVEC), _HALFVEC),
    _support_function("halfvec_mul", (_HALFVEC, _HALFVEC), _HALFVEC),
    _support_function("halfvec_concat", (_HALFVEC, _HALFVEC), _HALFVEC),
    _support_function("halfvec_lt", (_HALFVEC, _HALFVEC), _BOOL),
    _support_function("halfvec_le", (_HALFVEC, _HALFVEC), _BOOL),
    _support_function("halfvec_eq", (_HALFVEC, _HALFVEC), _BOOL),
    _support_function("halfvec_ne", (_HALFVEC, _HALFVEC), _BOOL),
    _support_function("halfvec_ge", (_HALFVEC, _HALFVEC), _BOOL),
    _support_function("halfvec_gt", (_HALFVEC, _HALFVEC), _BOOL),
    _support_function("halfvec_cmp", (_HALFVEC, _HALFVEC), _INT4),
    _support_function(
        "halfvec_l2_squared_distance",
        (_HALFVEC, _HALFVEC),
        _FLOAT8,
    ),
    _support_function(
        "halfvec_negative_inner_product",
        (_HALFVEC, _HALFVEC),
        _FLOAT8,
    ),
    _support_function(
        "halfvec_spherical_distance",
        (_HALFVEC, _HALFVEC),
        _FLOAT8,
    ),
    _support_function(
        "halfvec_accum",
        (_DOUBLE_PRECISION_ARRAY, _HALFVEC),
        _DOUBLE_PRECISION_ARRAY,
    ),
    _support_function("halfvec_avg", (_DOUBLE_PRECISION_ARRAY,), _HALFVEC),
    _support_function(
        "halfvec_combine",
        (_DOUBLE_PRECISION_ARRAY, _DOUBLE_PRECISION_ARRAY),
        _DOUBLE_PRECISION_ARRAY,
    ),
)
_HALFVEC_CAST_FUNCTIONS = (
    _support_function("halfvec", (_HALFVEC, _INTEGER, _BOOLEAN), _HALFVEC),
    _support_function(
        "halfvec_to_vector",
        (_HALFVEC, _INTEGER, _BOOLEAN),
        _VECTOR,
    ),
    _support_function(
        "vector_to_halfvec",
        (_VECTOR, _INTEGER, _BOOLEAN),
        _HALFVEC,
    ),
    _support_function(
        "array_to_halfvec",
        (_INTEGER_ARRAY, _INTEGER, _BOOLEAN),
        _HALFVEC,
    ),
    _support_function(
        "array_to_halfvec",
        (_REAL_ARRAY, _INTEGER, _BOOLEAN),
        _HALFVEC,
    ),
    _support_function(
        "array_to_halfvec",
        (_DOUBLE_PRECISION_ARRAY, _INTEGER, _BOOLEAN),
        _HALFVEC,
    ),
    _support_function(
        "array_to_halfvec",
        (_NUMERIC_ARRAY, _INTEGER, _BOOLEAN),
        _HALFVEC,
    ),
    _support_function(
        "halfvec_to_float4",
        (_HALFVEC, _INTEGER, _BOOLEAN),
        _REAL_ARRAY,
    ),
)

_BIT_DIRECT_FUNCTIONS = (
    _direct_function("hamming_distance", (_BIT, _BIT), _FLOAT8),
    _direct_function("jaccard_distance", (_BIT, _BIT), _FLOAT8),
)

_SPARSEVEC_TYPE_FUNCTIONS = (
    _support_function("sparsevec_in", (_CSTRING, _OID, _INTEGER), _SPARSEVEC),
    _support_function("sparsevec_out", (_SPARSEVEC,), _CSTRING),
    _support_function("sparsevec_typmod_in", (_CSTRING_ARRAY,), _INTEGER),
    _support_function("sparsevec_recv", (_INTERNAL, _OID, _INTEGER), _SPARSEVEC),
    _support_function("sparsevec_send", (_SPARSEVEC,), _BYTEA),
)
_SPARSEVEC_DIRECT_FUNCTIONS = (
    _direct_function("l2_distance", (_SPARSEVEC, _SPARSEVEC), _FLOAT8),
    _direct_function("inner_product", (_SPARSEVEC, _SPARSEVEC), _FLOAT8),
    _direct_function("cosine_distance", (_SPARSEVEC, _SPARSEVEC), _FLOAT8),
    _direct_function("l1_distance", (_SPARSEVEC, _SPARSEVEC), _FLOAT8),
    _direct_function("l2_norm", (_SPARSEVEC,), _FLOAT8),
    _direct_function("l2_normalize", (_SPARSEVEC,), _SPARSEVEC),
)
_SPARSEVEC_PRIVATE_FUNCTIONS = (
    _support_function("sparsevec_lt", (_SPARSEVEC, _SPARSEVEC), _BOOL),
    _support_function("sparsevec_le", (_SPARSEVEC, _SPARSEVEC), _BOOL),
    _support_function("sparsevec_eq", (_SPARSEVEC, _SPARSEVEC), _BOOL),
    _support_function("sparsevec_ne", (_SPARSEVEC, _SPARSEVEC), _BOOL),
    _support_function("sparsevec_ge", (_SPARSEVEC, _SPARSEVEC), _BOOL),
    _support_function("sparsevec_gt", (_SPARSEVEC, _SPARSEVEC), _BOOL),
    _support_function("sparsevec_cmp", (_SPARSEVEC, _SPARSEVEC), _INT4),
    _support_function(
        "sparsevec_l2_squared_distance",
        (_SPARSEVEC, _SPARSEVEC),
        _FLOAT8,
    ),
    _support_function(
        "sparsevec_negative_inner_product",
        (_SPARSEVEC, _SPARSEVEC),
        _FLOAT8,
    ),
)
_SPARSEVEC_CAST_FUNCTIONS = (
    _support_function("sparsevec", (_SPARSEVEC, _INTEGER, _BOOLEAN), _SPARSEVEC),
    _support_function(
        "vector_to_sparsevec",
        (_VECTOR, _INTEGER, _BOOLEAN),
        _SPARSEVEC,
    ),
    _support_function(
        "sparsevec_to_vector",
        (_SPARSEVEC, _INTEGER, _BOOLEAN),
        _VECTOR,
    ),
    _support_function(
        "halfvec_to_sparsevec",
        (_HALFVEC, _INTEGER, _BOOLEAN),
        _SPARSEVEC,
    ),
    _support_function(
        "sparsevec_to_halfvec",
        (_SPARSEVEC, _INTEGER, _BOOLEAN),
        _HALFVEC,
    ),
    _support_function(
        "array_to_sparsevec",
        (_INTEGER_ARRAY, _INTEGER, _BOOLEAN),
        _SPARSEVEC,
    ),
    _support_function(
        "array_to_sparsevec",
        (_REAL_ARRAY, _INTEGER, _BOOLEAN),
        _SPARSEVEC,
    ),
    _support_function(
        "array_to_sparsevec",
        (_DOUBLE_PRECISION_ARRAY, _INTEGER, _BOOLEAN),
        _SPARSEVEC,
    ),
    _support_function(
        "array_to_sparsevec",
        (_NUMERIC_ARRAY, _INTEGER, _BOOLEAN),
        _SPARSEVEC,
    ),
)

_FUNCTION_ENTRIES = (
    *_VECTOR_TYPE_FUNCTIONS,
    *_VECTOR_DIRECT_FUNCTIONS,
    *_VECTOR_PRIVATE_FUNCTIONS,
    *_VECTOR_CAST_FUNCTIONS,
    *_ACCESS_METHOD_FUNCTIONS,
    *_HALFVEC_TYPE_FUNCTIONS,
    *_HALFVEC_DIRECT_FUNCTIONS,
    *_HALFVEC_PRIVATE_FUNCTIONS,
    *_HALFVEC_CAST_FUNCTIONS,
    *_BIT_DIRECT_FUNCTIONS,
    *_SPARSEVEC_TYPE_FUNCTIONS,
    *_SPARSEVEC_DIRECT_FUNCTIONS,
    *_SPARSEVEC_PRIVATE_FUNCTIONS,
    *_SPARSEVEC_CAST_FUNCTIONS,
)

_AGGREGATE_ENTRIES = (
    _aggregate("avg", _VECTOR, _VECTOR),
    _aggregate("sum", _VECTOR, _VECTOR),
    _aggregate("avg", _HALFVEC, _HALFVEC),
    _aggregate("sum", _HALFVEC, _HALFVEC),
)

_OPERATOR_ENTRIES = (
    _operator("<->", _VECTOR, _FLOAT8),
    _operator("<#>", _VECTOR, _FLOAT8),
    _operator("<=>", _VECTOR, _FLOAT8),
    _operator("<+>", _VECTOR, _FLOAT8),
    _operator("+", _VECTOR, _VECTOR),
    _operator("-", _VECTOR, _VECTOR),
    _operator("*", _VECTOR, _VECTOR),
    _operator("||", _VECTOR, _VECTOR),
    _operator("<", _VECTOR, _BOOL),
    _operator("<=", _VECTOR, _BOOL),
    _operator("=", _VECTOR, _BOOL),
    _operator("<>", _VECTOR, _BOOL),
    _operator(">=", _VECTOR, _BOOL),
    _operator(">", _VECTOR, _BOOL),
    _operator("<->", _HALFVEC, _FLOAT8),
    _operator("<#>", _HALFVEC, _FLOAT8),
    _operator("<=>", _HALFVEC, _FLOAT8),
    _operator("<+>", _HALFVEC, _FLOAT8),
    _operator("+", _HALFVEC, _HALFVEC),
    _operator("-", _HALFVEC, _HALFVEC),
    _operator("*", _HALFVEC, _HALFVEC),
    _operator("||", _HALFVEC, _HALFVEC),
    _operator("<", _HALFVEC, _BOOL),
    _operator("<=", _HALFVEC, _BOOL),
    _operator("=", _HALFVEC, _BOOL),
    _operator("<>", _HALFVEC, _BOOL),
    _operator(">=", _HALFVEC, _BOOL),
    _operator(">", _HALFVEC, _BOOL),
    _operator("<~>", _BIT, _FLOAT8),
    _operator("<%>", _BIT, _FLOAT8),
    _operator("<->", _SPARSEVEC, _FLOAT8),
    _operator("<#>", _SPARSEVEC, _FLOAT8),
    _operator("<=>", _SPARSEVEC, _FLOAT8),
    _operator("<+>", _SPARSEVEC, _FLOAT8),
    _operator("<", _SPARSEVEC, _BOOL),
    _operator("<=", _SPARSEVEC, _BOOL),
    _operator("=", _SPARSEVEC, _BOOL),
    _operator("<>", _SPARSEVEC, _BOOL),
    _operator(">=", _SPARSEVEC, _BOOL),
    _operator(">", _SPARSEVEC, _BOOL),
)

_CAST_ENTRIES = (
    _cast(_VECTOR, _VECTOR, PostgreSQLCastContext.IMPLICIT),
    _cast(_VECTOR, _REAL_ARRAY, PostgreSQLCastContext.IMPLICIT),
    _cast(_INTEGER_ARRAY, _VECTOR, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_REAL_ARRAY, _VECTOR, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_DOUBLE_PRECISION_ARRAY, _VECTOR, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_NUMERIC_ARRAY, _VECTOR, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_HALFVEC, _HALFVEC, PostgreSQLCastContext.IMPLICIT),
    _cast(_HALFVEC, _VECTOR, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_VECTOR, _HALFVEC, PostgreSQLCastContext.IMPLICIT),
    _cast(_HALFVEC, _REAL_ARRAY, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_INTEGER_ARRAY, _HALFVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_REAL_ARRAY, _HALFVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_DOUBLE_PRECISION_ARRAY, _HALFVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_NUMERIC_ARRAY, _HALFVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_SPARSEVEC, _SPARSEVEC, PostgreSQLCastContext.IMPLICIT),
    _cast(_SPARSEVEC, _VECTOR, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_VECTOR, _SPARSEVEC, PostgreSQLCastContext.IMPLICIT),
    _cast(_SPARSEVEC, _HALFVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_HALFVEC, _SPARSEVEC, PostgreSQLCastContext.IMPLICIT),
    _cast(_INTEGER_ARRAY, _SPARSEVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_REAL_ARRAY, _SPARSEVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_DOUBLE_PRECISION_ARRAY, _SPARSEVEC, PostgreSQLCastContext.ASSIGNMENT),
    _cast(_NUMERIC_ARRAY, _SPARSEVEC, PostgreSQLCastContext.ASSIGNMENT),
)

_ENTRIES = (
    *_NATIVE_TYPE_ENTRIES,
    *_FUNCTION_ENTRIES,
    *_AGGREGATE_ENTRIES,
    *_OPERATOR_ENTRIES,
    *_CAST_ENTRIES,
)


def _build_pgvector_catalog() -> ConstructedExtensionCatalog:
    result = _construct_extension_catalog(_METADATA, _ENTRIES, ())
    if result.catalog is None:
        raise AssertionError("pgvector catalog construction must succeed")
    return result.catalog


PGVECTOR_V086_POSTGRESQL18_CATALOG = _build_pgvector_catalog()
