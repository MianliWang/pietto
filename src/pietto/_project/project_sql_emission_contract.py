"""Pure, explicit source realization over current verified planning authority."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from pietto.ast_nodes import DottedNameExpr, NameExpr, SourceDef, TypeDef
from pietto._project import project_sql_plan as plans
from pietto._project import project_sql_plan_target_assessment as targets
from pietto._project.project_sql_plan_verification import ProjectSQLPlanVerification
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_sql_emission_scopes import (
    EmissionLayout,
    build_emission_layout,
    reference_source_ports,
)
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_query_block_ir import ProjectIRReusedEffectiveOutput
from pietto.semantic.analyzer import _decimal_precision_scale_fact
from pietto.semantic.capability_profiles import (
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
)

__all__: tuple[str, ...] = ()

MAX_INPUT_BYTES = 1024 * 1024
MAX_SOURCES = 4096
MAX_FIELDS = 32768
MAX_DEPTH = 128
MAX_SQL_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_NODES = 32768
MAX_PARAMETERS = 32768
RELEASES = {"postgres": "18.6", "mysql": "8.4.12"}
CODES = {
    "PIE-B1001": "SOURCE_REALIZATION",
    "PIE-B1002": "REPRESENTATION",
    "PIE-B1003": "UNSUPPORTED_RULE",
    "PIE-B1004": "MISSING_EVIDENCE",
    "PIE-B1005": "PREMISE_CONFLICT",
    "PIE-B1006": "UNFULFILLED_REQUIREMENT",
    "PIE-B1007": "TARGET_RESOURCE",
    "PIE-B1008": "ARTIFACT_INTEGRITY",
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class InputError:
    kind: str
    message: str
    path: str | None = None


@dataclass(frozen=True, slots=True, eq=False)
class Blocker:
    code: str
    detail: str
    subject: object = None
    location: object = None
    related: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class BoundField:
    ordinal: int
    name: str
    column: str
    representation: bytes
    field: Any
    resolution: Any
    decimal_expression: Any
    decimal: Any


@dataclass(frozen=True, slots=True, eq=False)
class BoundSource:
    owner: Any
    selector: bytes
    namespace: str
    name: str
    fields: tuple[BoundField, ...]
    position: int


@dataclass(frozen=True, slots=True, eq=False)
class Premise:
    position: int
    key: str
    scope: object
    value: bytes


@dataclass(frozen=True, slots=True, eq=False, init=False)
class PreparedEmission:
    verification: ProjectSQLPlanVerification
    accepted_bytes: bytes
    normalized_bytes: bytes
    family: str
    release: str
    sources: tuple[BoundSource, ...]
    premises: tuple[Premise, ...]
    target_request: targets.ProjectSQLTargetRequest
    report: Any
    source_map: Any
    assessment: Any
    layout: EmissionLayout
    input_blockers: tuple[Blocker, ...]
    _accepted: tuple[object, ...]

    def __init__(self) -> None:
        raise TypeError("Emission inputs require explicit preparation.")

    @property
    def plan(self) -> plans.ProjectSQLPlan:
        value = self.verification.plan
        if type(value) is not plans.ProjectSQLPlan:
            raise ValueError("Prepared emission requires a concrete plan.")
        return value


@dataclass(frozen=True, slots=True, eq=False)
class PreparationFailure:
    errors: tuple[InputError, ...] = ()
    blockers: tuple[Blocker, ...] = ()
    diagnostics: tuple[Any, ...] = ()


def _error(
    errors, path, message="Invalid emission contract structure.", *, selector=False
):
    errors.append(
        InputError(
            "emission_selector" if selector else "emission_contract_schema",
            message,
            path,
        )
    )


def _object(value, keys, path, errors):
    if type(value) is not dict or set(value) != set(keys):
        _error(errors, path)
        return None
    return value


def _text(value):
    return (
        type(value) is str
        and bool(value)
        and not any(0xD800 <= ord(c) <= 0xDFFF for c in value)
    )


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _selector(value, path, errors, owners):
    value = _object(value, ("module", "kind", "name"), path, errors)
    if value is None:
        return None
    if (
        not _text(value["module"])
        or not _text(value["name"])
        or value["kind"] != "source"
    ):
        _error(errors, path, selector=True)
        return None
    matches = owners.get((value["module"], value["name"]), ())
    if len(matches) != 1:
        _error(errors, path, "Source selector is absent or ambiguous.", selector=True)
        return None
    return matches[0]


STORAGE_KEYS = {
    key: ("kind",)
    for key in (
        "pg_int2",
        "pg_int4",
        "pg_int8",
        "pg_bool",
        "pg_text",
        "pg_uuid",
        "pg_float8",
        "my_smallint",
        "my_int",
        "my_bigint",
        "my_bool01",
        "my_uuid_bytes",
        "my_double",
    )
} | {
    "pg_numeric": ("kind", "precision", "scale"),
    "my_decimal": ("kind", "precision", "scale"),
    "my_varchar": ("kind", "length"),
    "pg_timestamp": ("kind", "fractional_seconds"),
    "my_datetime": ("kind", "fractional_seconds"),
}
DOMAIN_KEYS = {
    "int_range": ("kind", "min", "max"),
    "bool01": ("kind",),
    "text": ("kind", "max_characters", "encoding", "collation", "padding"),
    "decimal": ("kind", "precision", "scale"),
    "timestamp": ("kind",),
    "uuid": ("kind", "encoding"),
    "finite_float": ("kind", "format"),
}


def _domain(value, path, errors):
    kind = value.get("kind") if type(value) is dict else None
    if type(kind) is not str or kind not in DOMAIN_KEYS:
        _error(errors, path)
        return False
    if _object(value, DOMAIN_KEYS[kind], path, errors) is None:
        return False
    valid = True
    if kind == "int_range":
        valid = all(
            type(value[k]) is str
            and re.fullmatch(r"-?(0|[1-9][0-9]*)", value[k])
            and len(value[k]) <= 128
            for k in ("min", "max")
        )
        if valid:
            valid = int(value["min"]) <= int(value["max"])
    elif kind == "text":
        valid = _integer(value["max_characters"]) and all(
            _text(value[k]) for k in ("encoding", "collation", "padding")
        )
    elif kind == "decimal":
        valid = (
            _integer(value["precision"], 1)
            and _integer(value["scale"])
            and value["scale"] <= value["precision"]
        )
    elif kind == "uuid":
        valid = value["encoding"] == "standard_bytes"
    elif kind == "finite_float":
        valid = value["format"] == "binary64"
    if not valid:
        _error(errors, path)
    return bool(valid)


def _representation(value, path, errors):
    value = _object(value, ("storage", "nullable", "domain"), path, errors)
    if value is None:
        return False
    count = len(errors)
    storage = value["storage"]
    kind = storage.get("kind") if type(storage) is dict else None
    if type(kind) is not str or kind not in STORAGE_KEYS:
        _error(errors, path + "/storage")
    elif _object(storage, STORAGE_KEYS[kind], path + "/storage", errors) is not None:
        if "precision" in storage and not (
            _integer(storage["precision"], 1)
            and _integer(storage["scale"])
            and storage["scale"] <= storage["precision"]
        ):
            _error(errors, path + "/storage")
        if "length" in storage and not _integer(storage["length"], 1):
            _error(errors, path + "/storage")
        if "fractional_seconds" in storage and (
            type(storage["fractional_seconds"]) is not int
            or storage["fractional_seconds"] != 6
        ):
            _error(errors, path + "/storage")
    if type(value["nullable"]) is not bool and value["nullable"] != "unknown":
        _error(errors, path + "/nullable")
    _domain(value["domain"], path + "/domain", errors)
    return len(errors) == count


def _logical_evidence(field, types):
    """Read retained resolution; reuse the existing Decimal rule at preparation only."""
    definition = field.evidence.field_def
    if definition is None or types is None:
        return None, None, None
    expression = definition.type_expr
    resolution = None
    seen = set()
    while expression is not None:
        if id(expression) in seen:
            return resolution, None, None
        seen.add(id(expression))
        matches = tuple(
            r
            for env in types.environments
            for r in env.find_type_expr(expression)
            if r.reference.type_expr is expression
        )
        if len(matches) != 1:
            return resolution, None, None
        current = matches[0]
        if resolution is None:
            resolution = current
        if current.direct_kind is ProjectResolvedTypeKind.BUILTIN:
            if current.canonical_name != "Decimal":
                return resolution, None, None
            fact, diagnostic = _decimal_precision_scale_fact(expression)
            return resolution, expression, fact if diagnostic is None else None
        if (
            current.direct_symbol is None
            or type(current.direct_symbol.target_occurrence.definition) is not TypeDef
        ):
            return resolution, None, None
        expression = current.direct_symbol.target_occurrence.definition.base
    return resolution, None, None


LOCAL_KEYS = {
    "row_domain_matches",
    "read_only_object",
    "value_domain",
    "encoding",
    "collation",
    "padding",
    "comparison_prefix_bytes",
}
STATEMENT_KEYS = {
    "session_sql_mode",
    "session_time_zone",
    "client_encoding",
    "identifier_case",
    "parameter_protocol",
    "operator_environment",
    "resource_limits",
}
RESOURCE_KEYS = {"sql_bytes", "artifact_bytes", "nodes", "parameters", "columns"}


def prepare_project_sql_emission(verification, data, *, target_request=None):
    errors: list[InputError] = []
    if type(verification) is not ProjectSQLPlanVerification:
        return PreparationFailure(
            errors=(InputError("emission_selector", "Invalid current planning roots."),)
        )
    diagnostics = getattr(getattr(verification, "completed", None), "diagnostics", ())
    unavailable = None
    view = None
    try:
        plans._require_roots(
            verification.completed,
            verification.analysis_bundle,
            verification.selected_owner,
        )
        if type(verification.plan) is plans.ProjectSQLPlanUnavailable:
            unavailable = verification.plan
            unavailable.__post_init__()
            if (
                unavailable.completed is not verification.completed
                or unavailable.analysis_bundle is not verification.analysis_bundle
                or unavailable.selected_owner is not verification.selected_owner
            ):
                raise ValueError("foreign unavailable root")
        else:
            view = inspect_project_sql_plan(verification)
    except (AttributeError, TypeError, ValueError):
        return PreparationFailure(
            errors=(
                InputError("emission_selector", "Invalid current planning roots."),
            ),
            diagnostics=diagnostics,
        )
    if type(data) is not bytes or len(data) > MAX_INPUT_BYTES:
        return PreparationFailure(
            errors=(
                InputError(
                    "emission_contract_schema",
                    "Emission input byte limit or type is invalid.",
                ),
            ),
            diagnostics=diagnostics,
        )
    try:
        document = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
        )
        pending = [(document, 1)]
        while pending:
            value, depth = pending.pop()
            if depth > MAX_DEPTH:
                raise ValueError("nesting limit")
            if type(value) is dict:
                pending.extend((v, depth + 1) for v in value.values())
            elif type(value) is list:
                pending.extend((v, depth + 1) for v in value)
        normalized = canonical(document)
    except (ValueError, UnicodeError, RecursionError):
        return PreparationFailure(
            errors=(
                InputError(
                    "emission_contract_schema", "Invalid UTF-8 JSON emission input."
                ),
            ),
            diagnostics=diagnostics,
        )
    if (
        _object(document, ("format", "target", "sources", "environment"), None, errors)
        is None
    ):
        return PreparationFailure(errors=tuple(errors), diagnostics=diagnostics)
    if document["format"] != "pietto.emission-contract.v1":
        _error(errors, "format")
    target = _object(document["target"], ("family", "release"), "target", errors)
    if target is not None and (
        target["family"] not in RELEASES if type(target["family"]) is str else True
    ):
        _error(errors, "target/family")
    if target is not None and (
        not _text(target["release"]) or target["release"].strip() != target["release"]
    ):
        _error(errors, "target/release")
    raw_sources = document["sources"]
    environment = document["environment"]
    if type(raw_sources) is not list or len(raw_sources) > MAX_SOURCES:
        _error(errors, "sources")
        raw_sources = []
    if type(environment) is not list:
        _error(errors, "environment")
        environment = []
    owners: dict[tuple[str, str], list[Any]] = {}
    semantic = verification.completed.semantic_result
    for owner in verification.analysis_bundle.root.owners:
        if type(owner.definition) is SourceDef:
            owners.setdefault(
                (semantic.modules[owner.module_position].path, owner.definition.name),
                [],
            ).append(owner)
    sources = []
    premise_inputs = [
        (p, "environment/" + str(i), None) for i, p in enumerate(environment)
    ]
    seen_sources = set()
    field_total = 0
    for position, raw in enumerate(raw_sources):
        path = f"sources/{position}"
        raw = _object(
            raw, ("selector", "relation", "scan", "fields", "premises"), path, errors
        )
        if raw is None:
            continue
        owner = _selector(raw["selector"], path + "/selector", errors, owners)
        if owner is not None:
            if id(owner) in seen_sources:
                _error(
                    errors,
                    path + "/selector",
                    "Duplicate source description.",
                    selector=True,
                )
            seen_sources.add(id(owner))
        relation = _object(
            raw["relation"], ("namespace", "name"), path + "/relation", errors
        )
        if relation is not None and not all(_text(relation[k]) for k in relation):
            _error(errors, path + "/relation")
        if raw["scan"] != "relation_rows":
            _error(errors, path + "/scan")
        if type(raw["fields"]) is not list:
            _error(errors, path + "/fields")
            continue
        field_total += len(raw["fields"])
        entries = (
            () if owner is None else verification.analysis_bundle.root.find_owner(owner)
        )
        original: tuple[Any, ...] = (
            entries[0].active_properties.relational.fields
            if len(entries) == 1 and type(entries[0]) is ProjectIRReusedEffectiveOutput
            else ()
        )
        bound_fields, ordinals, columns = [], set(), set()
        for j, raw_field in enumerate(raw["fields"]):
            fp = path + f"/fields/{j}"
            raw_field = _object(
                raw_field, ("ordinal", "name", "column", "representation"), fp, errors
            )
            if raw_field is None:
                continue
            start = len(errors)
            ordinal = raw_field["ordinal"]
            if (
                not _integer(ordinal)
                or ordinal in ordinals
                or (owner is not None and ordinal >= len(original))
            ):
                _error(errors, fp + "/ordinal", selector=True)
            else:
                ordinals.add(ordinal)
                if (
                    owner is not None
                    and raw_field["name"] != original[ordinal].evidence.name
                ):
                    _error(errors, fp + "/name", selector=True)
            if not _text(raw_field["name"]):
                _error(errors, fp + "/name")
            column = raw_field["column"]
            if not _text(column) or column in columns:
                _error(errors, fp + "/column")
            elif type(column) is str:
                columns.add(column)
            _representation(raw_field["representation"], fp + "/representation", errors)
            if len(errors) == start and owner is not None:
                field = original[ordinal]
                resolution, expression, decimal = _logical_evidence(
                    field, semantic.module_type_source_resolutions
                )
                bound_fields.append(
                    BoundField(
                        ordinal,
                        raw_field["name"],
                        column,
                        canonical(raw_field["representation"]),
                        field,
                        resolution,
                        expression,
                        decimal,
                    )
                )
        if type(raw["premises"]) is not list:
            _error(errors, path + "/premises")
        else:
            premise_inputs.extend(
                (p, path + f"/premises/{i}", owner)
                for i, p in enumerate(raw["premises"])
            )
        if owner is not None and relation is not None:
            sources.append(
                BoundSource(
                    owner,
                    canonical(raw["selector"]),
                    relation["namespace"],
                    relation["name"],
                    tuple(bound_fields),
                    position,
                )
            )
    if field_total > MAX_FIELDS:
        _error(errors, "sources", "Emission field mapping limit exceeded.")
    site_sources: dict[int, list[object]] = {}
    if view is not None:
        source_owners = {s.ref: s.source.owner for s in view.plan.sources}
        for expression, source_port in reference_source_ports(view.plan).values():
            site_sources.setdefault(id(expression.site), []).append(
                source_owners[source_port.owner]
            )
    premises = []
    for raw, path, enclosing in premise_inputs:
        raw = _object(raw, ("key", "scope", "value"), path, errors)
        if raw is None:
            continue
        start = len(errors)
        key, scope, value = raw["key"], raw["scope"], raw["value"]
        unbound_enclosing = (
            scope == "source" and enclosing is None and path.startswith("sources/")
        )
        bound_scope: object = None
        if scope == "statement":
            bound_scope = "statement"
        elif scope == "source" and enclosing is not None:
            bound_scope = enclosing
        elif type(scope) is dict and scope.get("kind") == "source":
            if (
                _object(scope, ("kind", "selector"), path + "/scope", errors)
                is not None
            ):
                bound_scope = _selector(
                    scope["selector"], path + "/scope/selector", errors, owners
                )
        elif type(scope) is dict and scope.get("kind") == "expression":
            if (
                _object(
                    scope,
                    ("kind", "source", "site", "context"),
                    path + "/scope",
                    errors,
                )
                is not None
            ):
                source_owner = _selector(
                    scope["source"], path + "/scope/source", errors, owners
                )
                refs = []
                for key_ref in ("site", "context"):
                    ref = _object(
                        scope[key_ref],
                        ("kind", "position"),
                        path + "/scope/" + key_ref,
                        errors,
                    )
                    refs.append(ref)
                    if ref is not None and (
                        not _text(ref["kind"]) or not _integer(ref["position"])
                    ):
                        _error(errors, path + "/scope/" + key_ref, selector=True)
                if len(errors) == start:
                    matches = tuple(
                        site
                        for site in (() if view is None else view.plan.expression_sites)
                        if site.ref.kind.value == refs[0]["kind"]
                        and site.ref.position == refs[0]["position"]
                        and site.block.kind.value == refs[1]["kind"]
                        and site.block.position == refs[1]["position"]
                    )
                    if len(matches) == 1 and any(
                        owner is source_owner
                        for owner in site_sources.get(id(matches[0]), ())
                    ):
                        bound_scope = (source_owner, matches[0])
        if bound_scope is None and len(errors) == start and not unbound_enclosing:
            _error(errors, path + "/scope", selector=True)
        if type(key) is not str or key not in LOCAL_KEYS | STATEMENT_KEYS:
            _error(errors, path + "/key")
        elif (key in STATEMENT_KEYS) != (bound_scope == "statement") or (
            key in {"row_domain_matches", "read_only_object"}
            and type(bound_scope) is tuple
        ):
            _error(errors, path + "/scope")
        elif key in {"row_domain_matches", "read_only_object"}:
            if type(value) is not bool:
                _error(errors, path + "/value")
        elif key == "value_domain":
            _domain(value, path + "/value", errors)
        elif key == "comparison_prefix_bytes":
            if not _integer(value, 1):
                _error(errors, path + "/value")
        elif key == "resource_limits":
            if (
                type(value) is not dict
                or not value
                or set(value) - RESOURCE_KEYS
                or any(not _integer(v) for v in value.values())
            ):
                _error(errors, path + "/value")
        elif not _text(value):
            _error(errors, path + "/value")
        if len(errors) == start and not unbound_enclosing:
            premises.append(Premise(len(premises), key, bound_scope, canonical(value)))
    if errors:
        return PreparationFailure(errors=tuple(errors), diagnostics=diagnostics)
    conflicts = []
    prior: dict[tuple[object, str], list[Premise]] = {}
    for premise in premises:
        scope_key = (
            ("statement",)
            if premise.scope == "statement"
            else tuple(id(v) for v in premise.scope)
            if type(premise.scope) is tuple
            else (id(premise.scope),)
        )
        bucket = prior.setdefault((scope_key, premise.key), [])
        if any(p.value != premise.value for p in bucket):
            conflicts.append(
                Blocker("PIE-B1005", "inconsistent_declared_scope", premise)
            )
        bucket.append(premise)
    if unavailable is not None:
        return PreparationFailure(
            blockers=tuple(conflicts)
            + tuple(
                Blocker("PIE-B1003", b.kind.value, b.owner, b.owner.definition.span)
                for b in unavailable.blockers
            ),
            diagnostics=diagnostics,
        )
    assert view is not None
    assert target is not None
    family, release = target["family"], target["release"]
    try:
        if target_request is None:
            target_request = targets.prepare_project_sql_target_request(
                CapabilityProfileTarget(
                    CapabilityProfileTargetKind.DATABASE,
                    "postgresql" if family == "postgres" else family,
                    release,
                )
            )
        t = target_request.target
        if t is None or (t.family, t.release) != (
            "postgresql" if family == "postgres" else family,
            release,
        ):
            raise ValueError("target mismatch")
        report = view.requirements().verification
        source_map = view.source_map().verification
        assessment = view.target_assessment(
            target_request, report_verification=report
        ).verification
        layout = build_emission_layout(verification)
    except (AttributeError, TypeError, ValueError):
        return PreparationFailure(
            errors=(
                InputError(
                    "emission_selector", "Target evidence is foreign or inconsistent."
                ),
            ),
            diagnostics=diagnostics,
        )
    result = object.__new__(PreparedEmission)
    values = (
        verification,
        data,
        normalized,
        family,
        release,
        tuple(sources),
        tuple(premises),
        target_request,
        report,
        source_map,
        assessment,
        layout,
        tuple(conflicts),
    )
    for name, value in zip(
        (
            "verification",
            "accepted_bytes",
            "normalized_bytes",
            "family",
            "release",
            "sources",
            "premises",
            "target_request",
            "report",
            "source_map",
            "assessment",
            "layout",
            "input_blockers",
        ),
        values,
        strict=True,
    ):
        object.__setattr__(result, name, value)
    object.__setattr__(result, "_accepted", values)
    return result


def source_family(source):
    callee = source.connector.callee
    if type(callee) is NameExpr:
        return {"postgres.table": "postgres", "mysql.table": "mysql"}.get(callee.name)
    if type(callee) is DottedNameExpr:
        families: dict[tuple[str, ...], str] = {
            ("postgres", "table"): "postgres",
            ("mysql", "table"): "mysql",
        }
        return families.get(callee.parts)
    return None
