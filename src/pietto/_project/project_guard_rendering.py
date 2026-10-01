"""Closed guarded statements linked from verified typed original fragments."""

from pietto._project.project_guard_program import (
    GuardParameterUse,
    NativeGuardStatement,
)
from pietto._project.project_guard_lowering import original_fragments, terminal_order
from pietto._project.project_sql_emission_ast import SQLSelect, resource_limits
from pietto._project.project_sql_emission_contract import BoundSource
from pietto._project.project_sql_emission_rendering import _Writer, _join_condition
from pietto._project.project_execution_binding_verification import native_arguments

__all__: tuple[str, ...] = ()


def render_guard(statement):
    from pietto._project.project_guard_verification import (
        verify_statement,
        verify_native_guard,
    )

    verify_statement(statement)
    p = statement.program
    if statement.kind == "data" and not statement.subjects:
        artifact = p.preparation.artifact
        arguments = native_arguments(
            artifact,
            tuple(
                s.site.position.literal.value
                for s in artifact.request.plan.literal_slots
            ),
        )
        uses = tuple(
            GuardParameterUse(
                "original", u.slot, u.server_index, arguments[u.server_index - 1], u
            )
            for u in artifact.parameter_uses
        )
        native = NativeGuardStatement(statement, artifact.rendered.sql, uses, arguments)
        verify_native_guard(native)
        return native
    if p.refinement is not None:
        from pietto._project.project_guard_lowering import refined_guard_syntax
        from pietto._project.project_refinement_rendering import render

        rendered = render(
            refined_guard_syntax(statement), p.preparation.artifact, _guards=statement
        )
        native = NativeGuardStatement(
            statement,
            rendered.sql,
            tuple(
                GuardParameterUse(u.domain, u.owner, u.index, u.value, u.original)
                for u in rendered.uses
            ),
            rendered.arguments,
        )
        verify_native_guard(native)
        return native
    artifact = p.preparation.artifact
    request = artifact.request
    family, prefix = request.family, p.prefix
    quote = '"' if family == "postgres" else "`"
    chunks, uses, assigned = [], [], []
    original_values = native_arguments(
        artifact,
        tuple(s.site.position.literal.value for s in request.plan.literal_slots),
    )
    events = artifact.rendered.events
    parameter_events = tuple(e for e in events if e.kind == "parameter")
    original_uses = dict(zip(parameter_events, artifact.parameter_uses, strict=True))
    references = {}
    for i, source in enumerate(request.sources):
        (ref,) = tuple(
            s.ref for s in request.plan.sources if s.source.owner is source.owner
        )
        references[ref] = prefix + "s" + str(i)
    size = 0

    def emit(text):
        nonlocal size
        data = text.encode() if type(text) is str else text
        size += len(data)
        if size > resource_limits(request)["sql_bytes"]:
            raise ValueError("GUARD_RESOURCE_LIMIT")
        chunks.append(data)

    def identifier(name):
        emit(quote + name.replace(quote, quote * 2) + quote)

    def parameter(domain, owner, value, original=None):
        if family == "postgres":
            matches = tuple(
                i for i, (d, o) in enumerate(assigned) if d == domain and o is owner
            )
            if matches:
                (index,) = matches
            else:
                index = len(assigned)
                assigned.append((domain, owner))
        else:
            index = len(uses)
        uses.append(GuardParameterUse(domain, owner, index + 1, value, original))
        emit("$" + str(index + 1) if family == "postgres" else "?")

    def controls(control):
        if family == "postgres":
            emit("CAST(")
        parameter("guard", control, control.value)
        if family == "postgres":
            emit(" AS BIGINT)")

    def cast_integer(value):
        emit(
            "CAST("
            + str(value)
            + (" AS BIGINT)" if family == "postgres" else " AS SIGNED)")
        )

    def column(alias, name):
        identifier(alias)
        emit(".")
        identifier(name)

    def names(items):
        for i, item in enumerate(items):
            if i:
                emit(", ")
            identifier(item)

    def cte_open(name, columns):
        identifier(name)
        emit(" (")
        names(columns)
        emit(") AS MATERIALIZED (" if family == "postgres" else ") AS (")

    def relation(item):
        producer = item.producer
        if type(producer) is BoundSource:
            index = next(i for i, s in enumerate(request.sources) if s is producer)
            identifier(prefix + "s" + str(index))
        else:
            identifier(producer.symbol.name)
        emit(" AS ")
        identifier(item.symbol.name)

    def condition(subject):
        from pietto._project.project_refinement_rendering import _parameters

        if not subject.unit.equalities and subject.unit.predicate is None:
            emit("TRUE")
            return
        writer = _Writer(request)
        _join_condition(writer, subject.unit)
        data = b"".join(writer.chunks)
        leaves = (
            ()
            if subject.unit.predicate is None
            else _parameters(subject.unit.predicate)
        )
        pending = iter(leaves)
        for event in writer.events:
            if event.kind == "parameter":
                leaf = next(pending)
                if event.subject is not leaf.site.ref:
                    raise ValueError("GUARD_PARAMETER_SOURCE")
                use = leaf.use
                parameter(
                    "original", use.slot, original_values[use.server_index - 1], use
                )
            else:
                emit(data[event.start : event.end])
        if next(pending, None) is not None:
            raise ValueError("GUARD_PARAMETER_DENOMINATOR")

    extra, ordering = terminal_order(p)
    public = tuple(prefix + "v" + str(i) for i in range(len(p.output.columns)))
    order_names = tuple(x[0] for x in extra)
    all_data = public + order_names
    data_name, guard_name, wire_name = (prefix + s for s in ("data", "guards", "wire"))
    channel = prefix + "channel"
    guards = tuple(prefix + "g" + str(i) for i in range(len(statement.subjects)))
    if 1 + len(guards) + len(all_data) > resource_limits(request)["columns"]:
        raise ValueError("GUARD_RESOURCE_LIMIT")
    emit("WITH ")
    comma = False
    for index, (source, fields) in enumerate(
        zip(request.sources, p.source_reads, strict=True)
    ):
        if comma:
            emit(", ")
        comma = True
        marker = prefix + "materialization"
        columns = fields + ((marker,) if family == "mysql" or not fields else ())
        cte_open(prefix + "s" + str(index), columns)
        emit("SELECT ")
        for j, name in enumerate(fields):
            if j:
                emit(", ")
            column("s", name)
        if family == "mysql" or not fields:
            if fields:
                emit(", ")
            emit("MAX(1) OVER ()" if family == "mysql" else "1")
            emit(" AS ")
            identifier(marker)
        emit(" FROM ")
        identifier(source.namespace)
        emit(".")
        identifier(source.name)
        emit(" AS ")
        identifier("s")
        emit(")")
    for fragment in original_fragments(p):
        if comma:
            emit(", ")
        comma = True
        unit, final = fragment.unit, fragment.position == len(p.output.units) - 1
        if final:
            name, columns = data_name, all_data
        elif type(artifact.ast) is SQLSelect:
            cte = artifact.ast.ctes[fragment.position]
            name, columns = cte.symbol.name, tuple(c.name for c in cte.columns)
        else:
            name, columns = unit.symbol.name, tuple(c.name for c in unit.cte_columns)
        marker = prefix + "materialization"
        cte_open(name, columns + ((marker,) if family == "mysql" else ()))
        if family == "mysql":
            emit("SELECT ")
            for i, n in enumerate(columns):
                if i:
                    emit(", ")
                column("b", n)
            emit(", MAX(1) OVER () AS ")
            identifier(marker)
            emit(" FROM (")
        labels = (
            {c.export.ref: public[i] for i, c in enumerate(unit.columns)}
            if final
            else {}
        )
        injected = False
        for event in fragment.events:
            if (
                final
                and extra
                and event.kind == "syntax"
                and event.role == "from"
                and not injected
            ):
                for new_name, alias, read, _item in extra:
                    emit(", ")
                    column(alias, read)
                    emit(" AS ")
                    identifier(new_name)
                injected = True
            if event.kind == "parameter":
                use = original_uses[event]
                parameter(
                    "original", use.slot, original_values[use.server_index - 1], use
                )
            elif event.subject in references and event.role in (
                "namespace",
                "join_namespace",
                "set_namespace",
                "qualifier",
                "join_qualifier",
                "set_qualifier",
            ):
                continue
            elif event.subject in references and event.role in (
                "relation",
                "join_relation",
                "set_relation",
            ):
                identifier(references[event.subject])
            elif (
                event.kind == "identifier"
                and event.role == "label"
                and event.subject in labels
            ):
                identifier(labels[event.subject])
            else:
                emit(artifact.rendered.sql[event.start : event.end])
        if family == "mysql":
            emit(") AS ")
            identifier("b")
        emit(")")
    if statement.kind != "data":
        emit(", ")
        cte_open(guard_name, guards)
        emit("SELECT ")
        for i, subject in enumerate(statement.subjects):
            if i:
                emit(", ")
            emit("CAST(CASE WHEN EXISTS (SELECT 1 FROM ")
            relation(subject.inputs[0])
            emit(" WHERE EXISTS (SELECT 1 FROM ")
            relation(subject.inputs[1])
            emit(" WHERE ")
            condition(subject)
            emit(" LIMIT ")
            controls(statement.controls[0])
            emit(" OFFSET ")
            controls(statement.controls[1])
            emit(
                ")) THEN 1 ELSE 0 END"
                + (" AS BIGINT)" if family == "postgres" else " AS SIGNED)")
            )
            emit(" AS ")
            identifier(guards[i])
        emit(")")
    if statement.kind == "guard":
        emit(" SELECT ")
        names(guards)
        emit(" FROM ")
        identifier(guard_name)
    elif statement.kind == "combined":
        emit(", ")
        cte_open(wire_name, (channel,) + guards + all_data)
        emit("SELECT ")
        cast_integer(0)
        for name in guards:
            emit(", ")
            column("g", name)
        for _ in all_data:
            emit(", NULL")
        emit(" FROM ")
        identifier(guard_name)
        emit(" AS ")
        identifier("g")
        emit(" UNION ALL SELECT ")
        cast_integer(1)
        for name in guards:
            emit(", ")
            column("g", name)
        for name in all_data:
            emit(", ")
            column("d", name)
        emit(" FROM ")
        identifier(guard_name)
        emit(" AS ")
        identifier("g")
        emit(" CROSS JOIN ")
        identifier(data_name)
        emit(" AS ")
        identifier("d")
        emit(" WHERE ")
        for i, name in enumerate(guards):
            if i:
                emit(" AND ")
            column("g", name)
            emit(" = 0")
        emit(") SELECT ")
        identifier(channel)
        for name in guards:
            emit(", ")
            identifier(name)
        for name, original in zip(public, p.output.columns, strict=True):
            emit(", ")
            identifier(name)
            emit(" AS ")
            identifier(original.label)
        for name in order_names:
            emit(", ")
            identifier(name)
        emit(" FROM ")
        identifier(wire_name)
        emit(" ORDER BY ")
        identifier(channel)
        emit(" ASC")
        for name, direction in ordering:
            emit(", ")
            identifier(name)
            emit(" " + direction.upper())
    else:
        emit(" SELECT ")
        for i, (name, original) in enumerate(
            zip(public, p.output.columns, strict=True)
        ):
            if i:
                emit(", ")
            identifier(name)
            emit(" AS ")
            identifier(original.label)
        emit(" FROM ")
        identifier(data_name)
        if ordering:
            emit(" ORDER BY ")
            for i, (name, direction) in enumerate(ordering):
                if i:
                    emit(", ")
                identifier(name)
                emit(" " + direction.upper())
    if family == "postgres":
        by_index = {u.index: u.value for u in uses}
        arguments = tuple(by_index[i] for i in range(1, len(assigned) + 1))
    else:
        arguments = tuple(u.value for u in uses)
    native = NativeGuardStatement(statement, b"".join(chunks), tuple(uses), arguments)
    verify_native_guard(native)
    return native
