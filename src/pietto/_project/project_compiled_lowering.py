"""Resolved-input assembly into the original typed dialect carriers/renderers."""

from dataclasses import dataclass, replace
from types import MappingProxyType
import json

from pietto._project.project_compiled_schema import Address, CompiledError, MAX_RECORDS
from pietto._project.project_completed_semantics import derive_compiled_semantics
from pietto._project.project_query_block_ir import (
    build_compiled_query_block_ir,
    CompiledIRReference,
)
from pietto._project.project_sql_plan import build_compiled_sql_plan, CompiledSQLPort
from pietto._project.project_sql_plan_verification import verify_compiled_sql_plan
from pietto._project.project_sql_plan_expressions import ProjectSQLStageKind
from pietto._project.project_sql_emission_contract import (
    CompiledPreparedEmission,
    BoundSource,
    BoundField,
    Premise,
    canonical,
)
from pietto._project import project_sql_emission_ast as ast
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_emission_scopes import (
    ScopeDefinition,
    ScopeUse,
    TerminalBinding,
)
from pietto._project.project_sql_emission_rendering import render_join_sql
from pietto._project.project_sql_emission import CompiledEmissionArtifact

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class CompiledBlock:
    ref: object
    kind: ProjectSQLStageKind


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSubject:
    ref: object


def emit_compiled(root, values):
    completed = derive_compiled_semantics(root, tuple(values))
    ir = build_compiled_query_block_ir(completed)
    plan = build_compiled_sql_plan(ir)
    verification = verify_compiled_sql_plan(plan)
    from pietto._project.project_sql_plan_requirements import (
        build_compiled_requirement_report,
    )

    report = build_compiled_requirement_report(verification)
    records, refs = root.records, plan.references
    from pietto._project.project_compiled_schema import selected_relations

    active = selected_relations(records, records[root.description.query])
    target = records[Address("target", 0)]
    contract = target.get("contract").encode()
    document = json.loads(contract)
    from pietto._project.project_scalar_meaning import acquire_scalar_meaning
    from pietto.semantic.model import DecimalPrecisionScale

    meaning = (
        acquire_scalar_meaning(verification)
        if any(
            r.address.kind == "field" and r.get("meaning") is not None
            for r in records.values()
        )
        else None
    )
    sources, source_columns = [], {}
    use_bindings = {}
    definitions = {d.ref: d for d in plan.definitions}
    facts = {f.address: f for f in completed.facts}
    declarations = {d.address: d for d in completed.declarations}
    source_records = tuple(
        r
        for r in records.values()
        if r.address.kind == "source" and r.address in active
    )
    if len(document["sources"]) != len(source_records):
        raise CompiledError("COMPILED_SOURCE_CONTRACT")
    for source_record, described in zip(
        source_records, document["sources"], strict=True
    ):
        ports = tuple(
            r
            for r in records.values()
            if r.address.kind == "port" and r.get("owner") == source_record.address
        )
        fields = []
        for field_ref, port in zip(source_record.get("fields"), ports, strict=True):
            record = records[field_ref]
            logical = plan.ports[port.address].field
            fields.append(
                BoundField(
                    record.get("ordinal"),
                    record.get("label"),
                    record.get("column"),
                    record.get("physical").encode(),
                    logical,
                    None,
                    None,
                    None
                    if record.get("decimal") is None
                    else DecimalPrecisionScale(*record.get("decimal")),
                    meaning,
                )
            )
        source = BoundSource(
            declarations[source_record.get("declaration")],
            canonical(described["selector"]),
            source_record.get("namespace"),
            source_record.get("name"),
            tuple(fields),
            source_record.address.position,
        )
        sources.append(source)
        source_columns[source_record.address] = tuple(
            rows.StageColumn(
                f.ordinal,
                f.column,
                refs[p.address],
                facts[p.address].realization,
                field=f,
                source_port=refs[p.address],
            )
            for f, p in zip(fields, ports, strict=True)
        )
    input_position = 0
    for record in records.values():
        if record.address.kind != "use" or record.get("consumer") not in active:
            continue
        producer = definitions[refs[record.get("producer")]]
        consumer = definitions[refs[record.get("consumer")]]
        bindings = []
        for address in record.get("ports"):
            canonical_port = plan.ports[address]
            reference = CompiledIRReference(plan.scope, "input_port", input_position)
            input_position += 1
            if input_position > MAX_RECORDS:
                raise CompiledError("COMPILED_EXPANSION_LIMIT")
            local = CompiledSQLPort(
                reference,
                refs[record.address],
                canonical_port.field,
                canonical_port.identity,
                canonical_port.ref,
            )
            bindings.append(TerminalBinding(canonical_port, canonical_port, local))
        use_bindings[record.address] = ScopeUse(
            CompiledSubject(refs[record.address]),
            ScopeDefinition(producer, producer.exports),
            ScopeDefinition(consumer, consumer.exports),
            tuple(bindings),
        )

    def premise_scope(scope):
        if scope == "statement":
            return scope
        if type(scope) is tuple:
            return (declarations[scope[0]], refs[scope[1]])
        return declarations[scope]

    premises = tuple(
        Premise(
            r.get("position"),
            r.get("key"),
            premise_scope(r.get("scope")),
            r.get("value").encode(),
        )
        for r in records.values()
        if r.address.kind == "premise"
    )
    subject_records = dict(
        {
            **{ref: None for ref in refs.values()},
            **{
                pair.input_port.ref: None
                for use in use_bindings.values()
                for pair in use.bindings
            },
            plan.scope: None,
        }
    )
    subjects = MappingProxyType(subject_records)
    request = CompiledPreparedEmission(
        verification,
        contract,
        canonical(document),
        target.get("family"),
        target.get("release"),
        tuple(sources),
        premises,
        tuple(use_bindings.values()),
        subjects,
        scalar_meaning=meaning,
        report=report,
    )
    source_by_ref = {
        record.address: source
        for record, source in zip(source_records, sources, strict=True)
    }
    bodies, columns_by_ref = {}, dict(source_columns)
    native_by_literal = {}
    for use in plan.parameter_uses:
        native_by_literal.setdefault(
            Address(use.original.ref.kind, use.original.ref.position), []
        ).append(use)
    seen_uses = {}

    def scalar(address, use, producer, alias, join_contexts=None):
        record = records[address]
        fact = facts[address]
        original = plan.expressions[address]
        if address.kind == "read":
            port = records[record.get("port")]
            symbol = None
            if join_contexts is not None:
                use = record.get("use")
                if use not in join_contexts:
                    raise CompiledError("COMPILED_MATCH_USE")
                producer, symbol, columns = join_contexts[use]
                column = columns[port.get("ordinal")]
            else:
                column = columns_by_ref[producer][port.get("ordinal")]
            if record.get("use") != use or port.get("owner") != producer:
                raise CompiledError("COMPILED_READ_SCOPE")
            binding = use_bindings[use].bindings[port.get("ordinal")]
            return rows.SQLStageReference(
                original, binding.input_port.ref, column, fact.realization, scope=symbol
            )
        if address.kind == "literal":
            site = next(
                s for s in plan.literal_sites if s.position.expression is original.ref
            )
            if address in native_by_literal:
                position = seen_uses.get(address, 0)
                uses = native_by_literal[address]
                if position >= len(uses):
                    raise CompiledError("COMPILED_PARAMETER_EXPANSION")
                native = uses[position]
                seen_uses[address] = position + 1
                fixed = next(
                    f for f in plan.fixed_envelope.values if f.slot is native.slot
                )
                leaf = parameters.SQLParameter(original, site, fixed, native)
            else:
                leaf = parameters.SQLLiteral(original, site, fact.value)
            return parameters.SQLAnchor(
                original,
                parameters.PHYSICAL[request.family][fact.value_type.resolved_type.name],
                leaf,
            )
        role, token = record.get("operator")
        operands = tuple(
            scalar(a, use, producer, alias, join_contexts)
            for a in record.get("operands")
        )
        if role == "unary" and type(operands[0]) in (
            parameters.SQLAnchor,
            parameters.SQLUnary,
        ):
            return parameters.SQLUnary(original, operands[0])
        kind = {
            "unary": "sign",
            "comparison": "comparison",
            "null_test": "null_test",
        }.get(role, "logical" if token in ("and", "or") else "arithmetic")
        return rows.SQLOperation(original, kind, operands, fact.realization)

    def read_column(address, use, producer, alias):
        value = scalar(address, use, producer, alias)
        if type(value) is not rows.SQLStageReference:
            raise CompiledError("COMPILED_REQUIRED_READ")
        return value.column

    units = tuple(
        r
        for r in records.values()
        if r.address.kind in ("row", "aggregate", "window", "result", "set", "join")
        and r.address in active
    )
    for index, record in enumerate(units):
        if record.get("layout")[-1] != index:
            raise CompiledError("COMPILED_UNIT_ORDER")
        if record.address.kind == "join":
            from pietto._project.project_sql_emission_joins import (
                build_compiled_unit as build_join,
            )

            images, contexts = [], {}
            for ordinal, use_address in enumerate(record.get("inputs")):
                producer_address = records[use_address].get("producer")
                symbol = ast.SQLSymbol(
                    ordinal, refs[use_address], record.get("layout")[2][ordinal]
                )
                reads = tuple(
                    replace(c, scope=symbol) for c in columns_by_ref[producer_address]
                )
                source = source_by_ref.get(producer_address)
                images.append(
                    (
                        source if source is not None else bodies[producer_address],
                        refs[producer_address] if source is not None else None,
                        symbol,
                        reads,
                        use_bindings[use_address],
                    )
                )
                contexts[use_address] = (producer_address, symbol, reads)
            predicate = (
                None
                if record.get("predicate") is None
                else scalar(record.get("predicate"), None, None, "", contexts)
            )
            body = build_join(plan, record, tuple(images), predicate)
            bodies[record.address] = body
            columns_by_ref[record.address] = tuple(
                replace(c.column, name=body.cte_columns[i].name)
                for i, c in enumerate(body.columns)
            )
            continue
        if record.address.kind == "set":
            from pietto._project.project_sql_emission_sets import build_compiled_unit

            producer_inputs = []
            for use_address in record.get("operands"):
                producer_address = records[use_address].get("producer")
                source = source_by_ref.get(producer_address)
                producer_inputs.append(
                    (
                        source if source is not None else bodies[producer_address],
                        next(
                            (
                                s
                                for s in plan.sources
                                if s.ref is refs[producer_address]
                            ),
                            None,
                        ),
                        columns_by_ref[producer_address],
                        use_bindings[use_address],
                    )
                )
            definition = ScopeDefinition(
                definitions[refs[record.address]],
                tuple(plan.ports[p] for p in record.get("outputs")),
            )
            body = build_compiled_unit(plan, record, definition, tuple(producer_inputs))
            bodies[record.address] = body
            names = record.get("layout")[1]
            columns_by_ref[record.address] = tuple(
                replace(c.column, name=names[i] if names else c.label)
                for i, c in enumerate(body.columns)
            )
            continue
        producer = record.get("input")
        name, native_names, alias, final, _position = record.get("layout")
        uses = tuple(
            r
            for r in records.values()
            if r.address.kind == "use" and r.get("consumer") == record.address
        )
        if len(uses) != 1:
            raise CompiledError("COMPILED_UNIT_USE")
        use = uses[0].address
        block = CompiledBlock(
            refs[record.address],
            ProjectSQLStageKind(record.get("stage"))
            if record.address.kind == "row"
            else ProjectSQLStageKind.AGGREGATE
            if record.address.kind == "aggregate"
            else ProjectSQLStageKind.WINDOW
            if record.address.kind == "window"
            else ProjectSQLStageKind.PROJECTION,
        )
        symbol = None if name is None else ast.SQLSymbol(index, block.ref, name)
        scan_symbol = ast.SQLSymbol(index, refs[use], alias)
        if producer in source_by_ref:
            scan = ast.RowScan(
                next(s for s in plan.sources if s.ref is refs[producer]),
                source_by_ref[producer],
                CompiledSubject(refs[use]),
                scan_symbol,
                use_bindings[use],
            )
        elif records[producer].get("owner") != record.get("owner"):
            scan = ast.RowNamedUse(
                bodies[producer],
                CompiledSubject(refs[use]),
                scan_symbol,
                use_bindings[use],
            )
        elif producer.kind == "join":
            scan = ast.RowJoinUse(
                bodies[producer], CompiledSubject(refs[use]), scan_symbol
            )
        else:
            scan = ast.RowStageUse(bodies[producer], block, scan_symbol)
        columns, terminals = [], []
        aggregation = None
        window_stage = None
        window_columns = {}
        if record.address.kind == "window":
            from pietto._project.project_sql_emission_windows import (
                build_compiled_stage as build_windows,
            )

            reads = {
                a: read_column(a, use, producer, alias)
                for a, r in records.items()
                if a.kind == "read" and r.get("use") == use
            }
            window_columns, window_stage = build_windows(plan, record, reads)
        if record.address.kind == "aggregate":
            from pietto._project.project_sql_emission_aggregation import (
                build_compiled_stage,
            )

            arguments = []
            for address in record.get("outputs"):
                expression = records[records[address].get("source")]
                children = (
                    expression.get("arguments")
                    if expression.address.kind == "aggregate_value"
                    else (expression.address,)
                )
                arguments.append(
                    None if not children else scalar(children[0], use, producer, alias)
                )
            built_columns, aggregation = build_compiled_stage(
                plan, record, tuple(arguments)
            )
            columns.extend(built_columns)
            terminals.extend(c.column for c in columns)
        else:
            for position, port_address in enumerate(record.get("outputs")):
                if port_address in window_columns:
                    output = window_columns[port_address]
                    columns.append(output)
                    terminals.append(output.column)
                    continue
                port = plan.ports[port_address]
                port_record = records[port_address]
                expression = port_record.get("source")
                value = scalar(expression, use, producer, alias)
                column = (
                    replace(
                        value.column,
                        position=position,
                        name=port.identity.name,
                        terminal=port.ref,
                        realization=facts[port_address].realization,
                        scope=None,
                    )
                    if type(value) is rows.SQLStageReference
                    else rows.StageColumn(
                        position,
                        port.identity.name,
                        port.ref,
                        facts[port_address].realization,
                        literal=parameters.LiteralOrigin(value, port, port)
                        if type(value) is parameters.SQLAnchor
                        or type(value) is parameters.SQLUnary
                        else None,
                    )
                )
                col_symbol = ast.SQLSymbol(position, port.ref, port.identity.name)
                if type(value) is rows.SQLStageReference:
                    output = ast.RowCarryColumn(
                        position,
                        port,
                        value.port,
                        value.column,
                        col_symbol,
                        port.identity.name,
                        column,
                    )
                else:
                    output = ast.RowValueColumn(
                        position,
                        port,
                        CompiledSubject(refs[expression]),
                        None,
                        refs[expression],
                        value,
                        col_symbol,
                        port.identity.name,
                        column,
                        None,
                    )
                columns.append(output)
                terminals.append(column)
        predicate_ref = (
            record.get("predicate") if record.address.kind == "row" else None
        )
        predicate = (
            None
            if predicate_ref is None
            else ast.RowPredicate(
                CompiledSubject(refs[predicate_ref]),
                refs[predicate_ref],
                scalar(predicate_ref, use, producer, alias),
            )
        )
        cte_columns = (
            tuple(
                ast.SQLSymbol(i, c.export.ref, label)
                for i, (c, label) in enumerate(zip(columns, native_names, strict=True))
            )
            if native_names
            else ()
        )
        definition = ScopeDefinition(
            definitions[refs[record.address]],
            tuple(plan.ports[p] for p in record.get("outputs")),
        )
        if record.address.kind == "result":
            from pietto._project.project_sql_emission_results import (
                build_compiled_result_body,
            )

            if producer not in bodies:
                raise CompiledError("COMPILED_RESULT_PRODUCER")
            order_reads = tuple(
                read_column(a, use, producer, alias) for a, _ in record.get("ordering")
            )
            body, extra_subjects = build_compiled_result_body(
                request=request,
                definition=definition,
                record=record,
                producer=bodies[producer],
                columns=tuple(columns),
                scan_symbol=scan_symbol,
                symbol=symbol,
                cte_columns=cte_columns,
                order_reads=order_reads,
            )
            subject_records.update((ref, None) for ref in extra_subjects)
        else:
            body = ast.RowBody(
                definition,
                block,
                index,
                scan,
                tuple(columns),
                tuple(terminals),
                predicate,
                final,
                symbol,
                cte_columns,
                aggregation=aggregation,
                window=window_stage,
            )
        bodies[record.address] = body
        columns_by_ref[record.address] = tuple(
            replace(
                c.column, position=i, name=native_names[i] if native_names else c.label
            )
            for i, c in enumerate(columns)
        )
    if any(seen_uses.get(a, 0) != len(uses) for a, uses in native_by_literal.items()):
        raise CompiledError("COMPILED_PARAMETER_INVENTORY")
    query = ast.CompiledSQLQuery(request, tuple(bodies.values()), len(records))
    rendered = render_join_sql(query)
    from pietto._project.project_guard_preparation import (
        CompiledPendingGuardScope,
        CompiledGuardedArtifact,
    )

    guarded = records[Address("policy", 0)].get("guarded")
    if not guarded and any(
        o.downstream_enforcement_required for o in plan.single_matches
    ):
        raise CompiledError("COMPILED_PENDING_GUARD")
    scope = (
        CompiledPendingGuardScope(
            request,
            plan.single_matches,
            tuple(o for o in plan.single_matches if o.downstream_enforcement_required),
        )
        if guarded
        else None
    )
    arguments = (
        request,
        query,
        rendered,
        tuple(
            ast.OriginalRequirement(
                entry,
                ast.original_rule(plan, entry, generated_scopes=len(query.units) > 1),
            )
            for entry in report.entries
        ),
        ast.row_generated_requirements(request, query),
        plan.fixed_envelope.values,
        plan.parameter_uses,
    )
    artifact = (
        CompiledEmissionArtifact(*arguments)
        if scope is None
        else CompiledGuardedArtifact(*arguments, guard_scope=scope)
    )
    from pietto._project.project_compiled_verification import verify_compiled_emission

    verify_compiled_emission(artifact, request)
    return artifact
