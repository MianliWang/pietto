from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from _static_audit_helpers import (
    read_text as _read,
)

from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import SemanticMetadataType
from pietto.ast_nodes import QueryDef, Script, TableDef, TypeDef
from pietto.errors import Severity
from pietto.ir import RelationIR, NullabilityIR, ScriptIR, TypeIR, TypeKindIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    analyze,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "docs/spec/type-alias-domain-refinement-boundary-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
METADATA_TEXT_PATH = REPO_ROOT / "src/pietto/_metadata/text.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"


def test_type_alias_kind_and_ir_kind_remain_the_alias_mechanism() -> None:
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)

    assert 'TYPE_ALIAS = "type_alias"' in semantic_model
    assert 'TYPE_ALIAS = "type_alias"' in ir_model


def test_alias_declaration_chain_and_nullability_preserve_current_facts() -> None:
    script = _parse(_alias_source())
    semantic_result = analyze(script)
    relation = _relation(semantic_result)
    source_schema = next(iter(semantic_result.model.source_row_schemas.values()))
    output_schema = semantic_result.model.relation_row_schemas[relation]

    assert _error_codes(semantic_result) == []
    email_field = source_schema.fields["email"]
    alias_email_field = output_schema.fields["alias_email"]

    for field in (email_field, output_schema.fields["email"], alias_email_field):
        assert field.resolved_type.name == "WorkEmail"
        assert field.resolved_type.kind is TypeKind.TYPE_ALIAS
        assert field.nullability is EffectiveNullability.NULLABLE

    work_email = _type_def(script, "WorkEmail")
    expansion = semantic_result.model.type_expansions[work_email.base]

    assert expansion.name == "Text"
    assert expansion.kind is TypeKind.BUILTIN


def test_alias_ir_preserves_declared_identity_and_canonical_target() -> None:
    ir = _compile(_alias_source())
    type_ir = _type_ir(ir, "WorkEmail")
    relation = _relation_ir(ir)
    email = relation.row_schema.fields[0]
    alias_email = relation.row_schema.fields[1]

    assert type_ir.declared_type.declared_name == "Email"
    assert type_ir.declared_type.kind is TypeKindIR.TYPE_ALIAS
    assert type_ir.canonical_type.canonical_name == "Text"
    assert type_ir.canonical_type.canonical_kind is TypeKindIR.BUILTIN

    for field in (email, alias_email):
        assert field.type_ref.declared_name == "WorkEmail"
        assert field.type_ref.kind is TypeKindIR.TYPE_ALIAS
        assert field.type_ref.nullability is NullabilityIR.NULLABLE


def test_alias_cycles_remain_fail_closed_with_pie_s2003() -> None:
    result = analyze(_parse("type A = A not null\n"))

    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [("PIE-S2003", "Type alias cycle involving A")]


def test_type_ensure_remains_parse_ast_only_not_domain_validation() -> None:
    script = _parse(
        "type Percent = Float not null ensure self between 0 and 1\n"
        "shape Metric:\n"
        "    score: Percent not null\n"
        'source metrics: Metric is postgres.table("metrics")\n'
        "table projected:\n"
        "    from metrics\n"
        "    select:\n"
        "        score\n"
    )
    percent = _type_def(script, "Percent")
    result = analyze(script)
    ir_result = build_ir(script, result.model)

    assert percent.ensures
    assert _error_codes(result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None

    type_ir = _type_ir(ir_result.ir, "Percent")
    assert not hasattr(type_ir, "ensures")

    artifact = build_semantic_metadata_artifact(
        path="phase36-slice8-type-ensure.pietto",
        script=script,
        semantic_result=result,
        ir=ir_result.ir,
    )
    serialized_type_fields = {field.name for field in fields(SemanticMetadataType)}

    assert artifact.metadata.types
    for forbidden in (
        "domain_constraints",
        "validation_rules",
        "units",
        "currency",
        "money",
        "native_domain",
        "domain_metadata",
        "runtime_validation",
        "coercion_rule",
    ):
        assert forbidden not in serialized_type_fields


def test_domain_refinement_and_currency_money_remain_deferred() -> None:
    catalog = _read(CATALOG_PATH)

    assert '"Currency"' not in catalog
    assert '"Money"' not in catalog


def test_no_domain_or_refinement_output_schema_expansion_was_added() -> None:
    sources = (
        _read(METADATA_MODEL_PATH),
        _read(METADATA_SERIALIZER_PATH),
        _read(METADATA_TEXT_PATH),
        _read(CLI_JSON_PATH),
    )

    for source in sources:
        lowered = source.lower()
        for forbidden in (
            "domain_constraints",
            "validation_rules",
            "units",
            "currency",
            "money",
            "native_domain",
            "domain_metadata",
            "runtime_validation",
            "coercion_rule",
        ):
            assert forbidden not in lowered, forbidden


def test_no_new_scalar_primitive_or_native_domain_carrier_was_added() -> None:
    sources = (
        _read(SEMANTIC_MODEL_PATH),
        _read(IR_MODEL_PATH),
        _read(METADATA_MODEL_PATH),
    )

    for source in sources:
        lowered = source.lower()
        for forbidden in (
            "native_domain",
            "domain_metadata",
            "runtime_validation",
            "coercion_rule",
        ):
            assert forbidden not in lowered, forbidden


def _alias_source() -> str:
    return (
        "type Email = Text not null\n"
        "type WorkEmail = Email nullable\n"
        "shape User:\n"
        "    email: WorkEmail nullable\n"
        'source users: User is postgres.table("users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "        alias_email = email\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile(source: str) -> ScriptIR:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _type_ir(script_ir: ScriptIR, name: str) -> TypeIR:
    matches = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, TypeIR) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _type_def(script: Script, name: str) -> TypeDef:
    matches = [
        definition
        for definition in script.definitions
        if isinstance(definition, TypeDef) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
