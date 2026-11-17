"""The DuckDB adapter's emission-contract reader (AD78.03).

It reads a `pietto.emission-contract.v1` document by the structural rules of
project emission, with the DuckDB target, scan and storage values of
docs/spec/duckdb-arrow-route-v1.md, and never hands the contract to the
PostgreSQL/MySQL reader. Structural failures are `InputError`s with the
messages that reader gives; everything that is valid structure but not
admitted on DuckDB is left to the adapter's compile refusals.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from pietto.ast_nodes import SourceDef
from pietto._project import project_sql_plan as plans
from pietto._project.project_query_block_ir import ProjectIRReusedEffectiveOutput
from pietto._project.project_sql_emission_contract import (
    MAX_DEPTH,
    MAX_FIELDS,
    MAX_INPUT_BYTES,
    MAX_SOURCES,
    InputError,
    Premise,
    _domain,
    _error,
    _finite,
    _integer,
    _nonfinite,
    _object,
    _selector,
    _text,
    canonical,
    unique_pairs,
    validate_resolved_premise,
)
from pietto._project.project_sql_emission_scopes import reference_source_ports

__all__: tuple[str, ...] = ()

FAMILY = "duckdb"
RELEASE = "2.0.0"
SCAN = "arrow_registration"
# Each storage kind and its members (docs/spec/duckdb-arrow-route-v1.md).
STORAGES = {
    "arrow_int64": ("kind",),
    "arrow_bool": ("kind",),
    "arrow_string": ("kind",),
    "arrow_float64": ("kind",),
    "arrow_date32": ("kind",),
    "arrow_timestamp_us": ("kind",),
    "arrow_decimal128": ("kind", "precision", "scale"),
}


@dataclass(frozen=True, slots=True, eq=False)
class DuckDBField:
    ordinal: int
    name: str
    column: str
    representation: dict[str, Any]


@dataclass(frozen=True, slots=True, eq=False)
class DuckDBSource:
    owner: Any
    selector: dict[str, Any]
    namespace: str
    name: str
    fields: tuple[DuckDBField, ...]


@dataclass(frozen=True, slots=True, eq=False)
class DuckDBContract:
    """A structurally valid DuckDB contract bound to the current plan roots."""

    release: str
    normalized: bytes
    environment: list[Any]
    sources: tuple[DuckDBSource, ...]
    premises: tuple[Premise, ...]


def _parsed(data: bytes) -> Any:
    """The JSON value, or the InputError the project emission reader gives."""

    def rejected(message: str) -> InputError:
        return InputError("emission_contract_schema", message)

    if data.startswith(b"\xef\xbb\xbf"):
        return rejected(
            "Emission contract starts with a UTF-8 byte-order mark; save it as"
            " UTF-8 without BOM."
        )
    try:
        document = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_float=_finite,
            parse_constant=_nonfinite,
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
        canonical(document)
    except UnicodeDecodeError:
        return rejected("Emission contract must be valid UTF-8.")
    except UnicodeEncodeError:
        return rejected(
            "Emission contract strings must not hold a lone surrogate escape"
            " (\\uD800-\\uDFFF)."
        )
    except json.JSONDecodeError as error:
        return rejected(
            f"Invalid JSON emission input: {error.msg} (line {error.lineno},"
            f" column {error.colno})."
        )
    except RecursionError:
        return rejected(f"Emission contract nests deeper than {MAX_DEPTH} levels.")
    except ValueError as error:
        return rejected(
            {
                "duplicate key": "Emission contract repeats a key in one object.",
                "nonfinite": "Emission contract numbers must be finite.",
                "nesting limit": f"Emission contract nests deeper than {MAX_DEPTH}"
                " levels.",
            }.get(
                str(error),
                f"Invalid JSON emission input: {str(error).partition(';')[0]}.",
            )
        )
    return document


def _representation(value: Any, path: str, errors: list[InputError]) -> bool:
    value = _object(value, ("storage", "nullable", "domain"), path, errors)
    if value is None:
        return False
    count = len(errors)
    storage = value["storage"]
    kind = storage.get("kind") if type(storage) is dict else None
    if type(kind) is not str or kind not in STORAGES:
        _error(
            errors,
            path + "/storage",
            f"Storage kind must be one of: {', '.join(STORAGES)}.",
        )
    elif (
        _object(storage, STORAGES[kind], path + "/storage", errors) is not None
        and "precision" in storage
        and not (
            _integer(storage["precision"], 1)
            and _integer(storage["scale"])
            and storage["scale"] <= storage["precision"]
        )
    ):
        _error(errors, path + "/storage")
    if type(value["nullable"]) is not bool and value["nullable"] != "unknown":
        _error(errors, path + "/nullable")
    _domain(value["domain"], path + "/domain", errors)
    return len(errors) == count


def read_duckdb_contract(
    verification: Any, data: bytes, *, read_sources_only: bool = False
) -> DuckDBContract | tuple[InputError, ...]:
    """Read `data` for the verified plan; `read_sources_only` (compile_query)
    keeps, once the whole contract is valid and its premises agree, only the
    sources the plan reads and the premises scoped to them or the statement,
    as the project emission reader does."""
    if type(data) is not bytes or len(data) > MAX_INPUT_BYTES:
        return (
            InputError(
                "emission_contract_schema",
                "Emission input byte limit or type is invalid.",
            ),
        )
    document = _parsed(data)
    if type(document) is InputError:
        return (document,)
    errors: list[InputError] = []
    if (
        _object(document, ("format", "target", "sources", "environment"), None, errors)
        is None
    ):
        return tuple(errors)
    if document["format"] != "pietto.emission-contract.v1":
        _error(errors, "format")
    target = _object(document["target"], ("family", "release"), "target", errors)
    if target is not None and target["family"] != FAMILY:
        _error(errors, "target/family")
    if target is not None and (
        not _text(target["release"]) or target["release"].strip() != target["release"]
    ):
        _error(errors, "target/release")
    raw_sources, environment = document["sources"], document["environment"]
    if type(raw_sources) is not list or len(raw_sources) > MAX_SOURCES:
        _error(errors, "sources")
        raw_sources = []
    if type(environment) is not list:
        _error(errors, "environment")
        environment = []
    plan = verification.plan
    available = type(plan) is plans.ProjectSQLPlan
    owners: dict[tuple[str, str], list[Any]] = {}
    semantic = verification.completed.semantic_result
    for owner in verification.analysis_bundle.root.owners:
        if type(owner.definition) is SourceDef:
            owners.setdefault(
                (semantic.modules[owner.module_position].path, owner.definition.name),
                [],
            ).append(owner)
    sources: list[DuckDBSource] = []
    premise_inputs = [
        (p, "environment/" + str(i), None) for i, p in enumerate(environment)
    ]
    seen: set[int] = set()
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
            if id(owner) in seen:
                _error(
                    errors,
                    path + "/selector",
                    "Duplicate source description.",
                    selector=True,
                )
            seen.add(id(owner))
        relation = _object(
            raw["relation"], ("namespace", "name"), path + "/relation", errors
        )
        if relation is not None and not all(_text(relation[k]) for k in relation):
            _error(errors, path + "/relation")
        if raw["scan"] != SCAN:
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
        fields, ordinals, columns = [], set(), set()
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
                _error(
                    errors,
                    fp + "/ordinal",
                    "Field ordinal must be a unique integer"
                    + (
                        f" from 0 to {len(original) - 1}."
                        if owner is not None and original
                        else " of at least 0."
                    ),
                    selector=True,
                )
            else:
                ordinals.add(ordinal)
                if (
                    owner is not None
                    and raw_field["name"] != original[ordinal].evidence.name
                ):
                    _error(
                        errors,
                        fp + "/name",
                        f"Field ordinal {ordinal} must be named"
                        f" {original[ordinal].evidence.name}.",
                        selector=True,
                    )
            if not _text(raw_field["name"]):
                _error(errors, fp + "/name")
            column = raw_field["column"]
            if not _text(column) or column in columns:
                _error(errors, fp + "/column")
            elif type(column) is str:
                columns.add(column)
            _representation(raw_field["representation"], fp + "/representation", errors)
            if len(errors) == start and owner is not None:
                fields.append(
                    DuckDBField(
                        ordinal,
                        raw_field["name"],
                        column,
                        raw_field["representation"],
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
                DuckDBSource(
                    owner,
                    raw["selector"],
                    relation["namespace"],
                    relation["name"],
                    tuple(fields),
                )
            )
    if field_total > MAX_FIELDS:
        _error(errors, "sources", "Emission field mapping limit exceeded.")
    site_sources: dict[int, list[object]] = {}
    if available:
        source_owners = {s.ref: s.source.owner for s in plan.sources}
        for expression, source_port in reference_source_ports(plan).values():
            site_sources.setdefault(id(expression.site), []).append(
                source_owners[source_port.owner]
            )
    premises: list[Premise] = []
    for raw, path, enclosing in premise_inputs:
        raw = _object(raw, ("key", "scope", "value"), path, errors)
        if raw is None:
            continue
        start = len(errors)
        key, scope, value = raw["key"], raw["scope"], raw["value"]
        unbound_enclosing = (
            scope == "source" and enclosing is None and path.startswith("sources/")
        )
        bound: object = None
        if scope == "statement":
            bound = "statement"
        elif scope == "source" and enclosing is not None:
            bound = enclosing
        elif type(scope) is dict and scope.get("kind") == "source":
            if (
                _object(scope, ("kind", "selector"), path + "/scope", errors)
                is not None
            ):
                bound = _selector(
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
                for name in ("site", "context"):
                    ref = _object(
                        scope[name],
                        ("kind", "position"),
                        path + "/scope/" + name,
                        errors,
                    )
                    refs.append(ref)
                    if ref is not None and (
                        not _text(ref["kind"]) or not _integer(ref["position"])
                    ):
                        _error(errors, path + "/scope/" + name, selector=True)
                if len(errors) == start:
                    matches = tuple(
                        site
                        for site in (plan.expression_sites if available else ())
                        if site.ref.kind.value == refs[0]["kind"]
                        and site.ref.position == refs[0]["position"]
                        and site.block.kind.value == refs[1]["kind"]
                        and site.block.position == refs[1]["position"]
                    )
                    if len(matches) == 1 and any(
                        owner is source_owner
                        for owner in site_sources.get(id(matches[0]), ())
                    ):
                        bound = (source_owner, matches[0])
        if bound is None and len(errors) == start and not unbound_enclosing:
            _error(errors, path + "/scope", selector=True)
        validate_resolved_premise(
            key,
            "statement"
            if bound == "statement"
            else "expression"
            if type(bound) is tuple
            else "source",
            value,
            path,
            errors,
        )
        if len(errors) == start and not unbound_enclosing:
            premises.append(Premise(len(premises), key, bound, canonical(value)))
    if errors:
        return tuple(errors)
    assert target is not None
    contract = DuckDBContract(
        target["release"],
        canonical(document),
        environment,
        tuple(sources),
        tuple(premises),
    )
    if not read_sources_only or not available or conflicts(contract.premises):
        return contract
    read = {id(binding.source.owner) for binding in plan.sources}
    bound_premises = iter(premises)  # one per raw premise, in input order

    def kept(raws: list[Any]) -> list[Any]:
        return [
            raw
            for raw in raws
            if (scope := next(bound_premises).scope) == "statement"
            or id(scope[0] if type(scope) is tuple else scope) in read
        ]

    # A kept premise declared in an unread entry is statement or dict-scoped,
    # so it moves to `environment` unchanged.
    trimmed = document | {"sources": [], "environment": kept(environment)}
    for raw, source in zip(raw_sources, sources, strict=True):
        premises_kept = kept(raw["premises"])
        if id(source.owner) in read:
            trimmed["sources"].append(raw | {"premises": premises_kept})
        else:
            trimmed["environment"] += premises_kept
    assert next(bound_premises, None) is None
    return read_duckdb_contract(verification, canonical(trimmed))


def conflicts(premises: tuple[Premise, ...]) -> tuple[Premise, ...]:
    """Each later declaration of a key in one scope whose value differs from
    an earlier one (rule 1)."""
    result = []
    prior: dict[tuple[object, str], list[Premise]] = {}
    for premise in premises:
        scope = premise.scope
        scope_key = (
            ("statement",)
            if scope == "statement"
            else tuple(id(v) for v in scope)
            if type(scope) is tuple
            else (id(scope),)
        )
        bucket = prior.setdefault((scope_key, premise.key), [])
        if any(p.value != premise.value for p in bucket):
            result.append(premise)
        bucket.append(premise)
    return tuple(result)
