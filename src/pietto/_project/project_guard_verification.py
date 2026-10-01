"""Independent complete original-subject and actual guard-byte correspondence."""

import re

from pietto._project.project_guard_preparation import verify_preparation
from pietto._project.project_guard_program import (
    GuardProgram,
    GuardSubject,
    GuardStatement,
    GuardControl,
    GuardParameterUse,
    NativeGuardStatement,
)
from pietto._project.project_result_output import verify_output, source_read_columns
from pietto._project.project_sql_emission_ast import SQLSelect, resource_limits
from pietto._project.project_sql_emission_contract import BoundSource
from pietto._project.project_sql_emission_joins import JoinBody
from pietto._project.project_sql_emission_results import RowResultBody
from pietto._project.project_sql_emission_parameters import same_value
from pietto._project.project_refinement_verification import _Bytes

__all__: tuple[str, ...] = ()


def need(condition, reason):
    if not condition:
        raise ValueError("GUARD_" + reason)


def verify_program(program):
    need(type(program) is GuardProgram, "PROGRAM")
    p = program.preparation
    obligations = verify_preparation(p)
    output = program.output
    verify_output(output, p.artifact, output.contract, binding=output.binding)
    need(output.guarded is p or not obligations, "OUTPUT_PURPOSE")
    if program.refinement is not None:
        from pietto._project.project_refinement_verification import verify_refinement

        verify_refinement(program.refinement)
        need(
            program.refinement.original is p.artifact
            and program.refinement.output is output,
            "REFINEMENT_ROOT",
        )
    expected = []
    for i, obligation in enumerate(obligations):
        for j, (reference, pair) in enumerate(
            zip(obligation.joins, obligation.input_pairs, strict=True)
        ):
            units = tuple(
                u
                for u in output.units
                if type(u) is JoinBody and u.join.ref is reference
            )
            need(len(units) == 1, "SUBJECT_BOUNDARY")
            unit = units[0]
            need(
                len(pair) == len(unit.inputs) == 2
                and all(
                    item.original.ref is root
                    for item, root in zip(unit.inputs, pair, strict=True)
                ),
                "SUBJECT_INPUT_PAIRS",
            )
            expected.append((obligation, i, j, unit))
    need(
        type(program.subjects) is tuple and len(program.subjects) == len(expected),
        "SUBJECT_DENOMINATOR",
    )
    for subject, (obligation, i, j, unit) in zip(
        program.subjects, expected, strict=True
    ):
        need(
            type(subject) is GuardSubject
            and subject.obligation is obligation
            and type(subject.request_position) is int
            and subject.request_position == i
            and type(subject.boundary_position) is int
            and subject.boundary_position == j
            and subject.unit is unit
            and subject.inputs is unit.inputs,
            "SUBJECT_IDENTITY",
        )
    need(
        type(program.prefix) is str
        and re.fullmatch(r"__pietto_guard_(?:[1-9][0-9]*_)?", program.prefix)
        is not None,
        "NAMESPACE",
    )
    names = [f.column for s in p.artifact.request.sources for f in s.fields]
    names += [c.label for u in output.units for c in u.columns]
    names += [
        u.symbol.name for u in output.units if getattr(u, "symbol", None) is not None
    ]
    if p.artifact.request.family == "mysql":
        names = [n.casefold() for n in names]
    need(not any(n.startswith(program.prefix) for n in names), "NAMESPACE_CAPTURE")
    need(program.source_reads == source_read_columns(output), "SOURCE_READ_CLOSURE")


def verify_statement(statement):
    need(type(statement) is GuardStatement, "STATEMENT")
    verify_program(statement.program)
    need(statement.kind in ("guard", "combined", "data"), "STATEMENT_KIND")
    need(type(statement.subjects) is tuple, "SELECTED_SUBJECTS")
    positions = []
    for subject in statement.subjects:
        matches = tuple(
            i for i, s in enumerate(statement.program.subjects) if s is subject
        )
        need(len(matches) == 1, "SELECTED_SUBJECTS")
        positions.extend(matches)
    from pietto._project.project_single_match import ProjectSingleMatchProofKind

    required = []
    proofs = statement.program.preparation.artifact.request.plan.single_match_proofs
    for index, subject in enumerate(statement.program.subjects):
        static = tuple(
            proof
            for proof in proofs
            if proof.obligation is subject.obligation.ref
            and any(join is subject.unit.join.ref for join in proof.joins)
            and proof.source.source.kind
            in (
                ProjectSingleMatchProofKind.RIGHT_LIMIT,
                ProjectSingleMatchProofKind.RIGHT_GLOBAL,
            )
        )
        if not static:
            required.append(index)
    need(positions == required, "SELECTED_SUBJECT_COVERAGE")
    need(bool(positions) or statement.kind == "data", "EMPTY_GUARD_WORK")
    need(type(statement.controls) is tuple and len(statement.controls) == 2, "CONTROLS")
    for control, name in zip(
        statement.controls, ("witness_limit", "second_match_offset"), strict=True
    ):
        need(
            type(control) is GuardControl
            and control.kind == name
            and type(control.value) is int
            and control.value == 1,
            "SATURATION_CONTROL",
        )


class _Read(_Bytes):
    """Consume one closed native grammar; original scalar parsing is upstream-owned."""

    def __init__(self, native):
        self.statement = native.statement
        self.program = native.statement.program
        super().__init__(native, self.program.preparation.artifact, ())
        self.allocated = []

    def parameter(self, domain, owner, index, value, original=None):
        if self.family == "postgres" and self.program.refinement is not None:
            if domain == "guard":
                (position,) = tuple(
                    i for i, c in enumerate(self.statement.controls) if c is owner
                )
                index = self.base + position + 1
        elif self.family == "postgres":
            indexes = [
                i + 1
                for i, (d, o) in enumerate(self.allocated)
                if d == domain and o is owner
            ]
            if not indexes:
                self.allocated.append((domain, owner))
                index = len(self.allocated)
            else:
                need(len(indexes) == 1, "PARAMETER_IDENTITY")
                index = indexes[0]
        else:
            index = len(self.uses) + 1
        self.take("$" + str(index) if self.family == "postgres" else "?")
        need(len(self.uses) < len(self.native.uses), "PARAMETER_DENOMINATOR")
        actual = self.native.uses[len(self.uses)]
        need(
            type(actual) is GuardParameterUse
            and actual.domain == domain
            and actual.owner is owner
            and type(actual.index) is int
            and actual.index == index
            and actual.original is original
            and same_value(actual.value, value),
            "PARAMETER_CORRESPONDENCE",
        )
        self.uses.append((domain, owner, index, value))

    def control(self, control):
        if self.family == "postgres":
            self.take("CAST(")
        self.parameter("guard", control, 0, control.value)
        if self.family == "postgres":
            self.take(" AS BIGINT)")

    def column(self, alias, name):
        self.identifier(alias)
        self.take(".")
        self.identifier(name)

    def names(self, values):
        self.list(values, self.identifier)

    def cte(self, name, fields):
        self.identifier(name)
        self.take(" (")
        self.names(fields)
        self.take(") AS MATERIALIZED (" if self.family == "postgres" else ") AS (")

    def integer(self, n):
        self.take(
            "CAST("
            + str(n)
            + (" AS BIGINT)" if self.family == "postgres" else " AS SIGNED)")
        )

    def relation(self, item):
        if type(item.producer) is BoundSource:
            (i,) = tuple(
                i
                for i, s in enumerate(self.artifact.request.sources)
                if s is item.producer
            )
            self.identifier(self.program.prefix + "s" + str(i))
        else:
            self.identifier(item.producer.symbol.name)
        self.take(" AS ")
        self.identifier(item.symbol.name)

    def match(self, unit):
        count = 0
        for equality in unit.equalities:
            if count:
                self.take(" AND ")
            self.take("(")
            self.column(equality.left_scope.name, equality.left.name)
            self.take(" = ")
            self.column(equality.right_scope.name, equality.right.name)
            self.take(")")
            count += 1
        if unit.predicate is not None:
            if count:
                self.take(" AND ")
            self.scalar(unit.predicate, "")
            count += 1
        if not count:
            need(unit.join.kind.value == "cross", "MATCH_PREDICATE")
            self.take("TRUE")

    def refined(self):
        """Read upstream-verified CTEs, then reconstruct exact guard boundaries."""
        from pietto._project.project_refinement_rendering import Expr, conjunction, ref

        q = self.program.refinement
        need(self.statement.kind == "guard", "REFINED_STATEMENT")
        if q.statement.ctes:
            self.take("WITH RECURSIVE " if q.statement.recursive else "WITH ")
            for i, cte in enumerate(q.statement.ctes):
                if i:
                    self.take(", ")
                self.identifier(cte.name)
                self.take(" (")
                self.names(cte.columns)
                self.take(") AS (")
                self.query(cte.query)
                self.take(")")
            self.take(" ")

        def relation(item):
            if type(item.producer) is BoundSource:
                indexes = tuple(
                    i
                    for i, source in enumerate(q.original.request.sources)
                    if source is item.producer
                )
                need(len(indexes) == 1, "REFINED_SOURCE")
                name = q.prefix + "source" + str(indexes[0])
            else:
                matches = tuple(u for u in q.units if u.original is item.producer)
                need(len(matches) == 1, "REFINED_PRODUCER")
                name = matches[0].terminal
            self.identifier(name)
            self.take(" AS ")
            self.identifier(item.symbol.name)

        self.take("SELECT ")
        for i, subject in enumerate(self.statement.subjects):
            if i:
                self.take(", ")
            self.take("CAST(CASE WHEN EXISTS (SELECT 1 AS ")
            self.identifier(self.program.prefix + "one")
            self.take(" FROM ")
            relation(subject.inputs[0])
            self.take(" WHERE EXISTS (SELECT 1 AS ")
            self.identifier(self.program.prefix + "one")
            self.take(" FROM ")
            relation(subject.inputs[1])
            self.take(" WHERE ")
            unit = subject.unit
            predicates = [
                Expr(
                    "=",
                    (
                        ref(e.left_scope.name, e.left.name),
                        ref(e.right_scope.name, e.right.name),
                    ),
                )
                for e in unit.equalities
            ]
            if unit.predicate is not None:
                predicates.append(Expr("original_scalar", (unit.predicate, "")))
            self.expression(conjunction(*predicates))
            self.take(" LIMIT ")
            self.control(self.statement.controls[0])
            self.take(" OFFSET ")
            self.control(self.statement.controls[1])
            self.take(
                ")) THEN 1 ELSE 0 END"
                + (" AS BIGINT)" if self.family == "postgres" else " AS SIGNED)")
            )
            self.take(" AS ")
            self.identifier(self.program.prefix + "g" + str(i))
        self.finish()

    def run(self):
        if self.program.refinement is not None:
            self.refined()
            return
        p, statement = self.program, self.statement
        request, prefix = self.artifact.request, p.prefix
        original = self.artifact.rendered
        units = p.output.units
        extra, ordering = [], []
        terminal = units[-1]
        if type(terminal) is RowResultBody and terminal.order is not None:
            for i, item in enumerate(terminal.order.items):
                if terminal.distinct is None:
                    name = prefix + "o" + str(i)
                    extra.append((name, terminal.scan.symbol.name, item.read.name))
                else:
                    positions = tuple(
                        j
                        for j, c in enumerate(terminal.columns)
                        if c.read.terminal is item.read.terminal
                        and c.read.name == item.read.name
                    )
                    need(len(positions) == 1, "DISTINCT_ORDER")
                    name = prefix + "v" + str(positions[0])
                ordering.append((name, item.direction))
        public = tuple(prefix + "v" + str(i) for i in range(len(p.output.columns)))
        data_fields = public + tuple(x[0] for x in extra)
        guards = tuple(prefix + "g" + str(i) for i in range(len(statement.subjects)))
        channel = prefix + "channel"
        self.take("WITH ")
        source_names = {}
        for i, (source, reads) in enumerate(
            zip(request.sources, p.source_reads, strict=True)
        ):
            (reference,) = tuple(
                s.ref for s in request.plan.sources if s.source.owner is source.owner
            )
            source_names[reference] = prefix + "s" + str(i)
            if i:
                self.take(", ")
            marker = prefix + "materialization"
            self.cte(
                source_names[reference],
                reads + ((marker,) if self.family == "mysql" or not reads else ()),
            )
            self.take("SELECT ")
            for j, field in enumerate(reads):
                if j:
                    self.take(", ")
                self.column("s", field)
            if self.family == "mysql" or not reads:
                if reads:
                    self.take(", ")
                self.take("MAX(1) OVER ()" if self.family == "mysql" else "1")
                self.take(" AS ")
                self.identifier(marker)
            self.take(" FROM ")
            self.identifier(source.namespace)
            self.take(".")
            self.identifier(source.name)
            self.take(" AS ")
            self.identifier("s")
            self.take(")")
        opens = [e for e in original.events if e.role == "cte_body_open"]
        closes = [e for e in original.events if e.role == "cte_body_close"]
        need(len(opens) == len(closes) == len(units) - 1, "ORIGINAL_UNIT_DENOMINATOR")
        ranges = [(a.end, b.start) for a, b in zip(opens, closes, strict=True)]
        final = [e for e in original.events if e.role == "with_body"]
        need(len(final) == int(len(units) > 1), "ORIGINAL_FINAL_RANGE")
        ranges.append((final[0].end if final else 0, len(original.sql)))
        parameters = iter(self.artifact.parameter_uses)
        by_event = {}
        for event in original.events:
            if event.kind == "parameter":
                by_event[event] = next(parameters)
        need(next(parameters, None) is None, "ORIGINAL_PARAMETERS")
        for position, (unit, (start, end)) in enumerate(
            zip(units, ranges, strict=True)
        ):
            self.take(", ")
            last = position == len(units) - 1
            if last:
                name, fields = prefix + "data", data_fields
            elif type(self.artifact.ast) is SQLSelect:
                cte = self.artifact.ast.ctes[position]
                name, fields = cte.symbol.name, tuple(s.name for s in cte.columns)
            else:
                name, fields = unit.symbol.name, tuple(s.name for s in unit.cte_columns)
            self.cte(
                name,
                fields
                + ((prefix + "materialization",) if self.family == "mysql" else ()),
            )
            if self.family == "mysql":
                self.take("SELECT ")
                for i, field in enumerate(fields):
                    if i:
                        self.take(", ")
                    self.column("b", field)
                self.take(", MAX(1) OVER () AS ")
                self.identifier(prefix + "materialization")
                self.take(" FROM (")
            labels = (
                {c.export.ref: public[i] for i, c in enumerate(unit.columns)}
                if last
                else {}
            )
            added = False
            for event in original.events:
                if event.start < start or event.end > end:
                    continue
                if (
                    last
                    and extra
                    and event.kind == "syntax"
                    and event.role == "from"
                    and not added
                ):
                    for label, alias, column in extra:
                        self.take(", ")
                        self.column(alias, column)
                        self.take(" AS ")
                        self.identifier(label)
                    added = True
                if event.kind == "parameter":
                    use = by_event[event]
                    value = use.slot.site.position.literal.value
                    if self.family == "mysql" and use.slot.tag.value == "Bool":
                        value = int(value)
                    self.parameter("original", use.slot, 0, value, use)
                elif event.subject in source_names and event.role in (
                    "namespace",
                    "join_namespace",
                    "set_namespace",
                    "qualifier",
                    "join_qualifier",
                    "set_qualifier",
                ):
                    pass
                elif event.subject in source_names and event.role in (
                    "relation",
                    "join_relation",
                    "set_relation",
                ):
                    self.identifier(source_names[event.subject])
                elif (
                    event.kind == "identifier"
                    and event.role == "label"
                    and event.subject in labels
                ):
                    self.identifier(labels[event.subject])
                else:
                    self.take(original.sql[event.start : event.end].decode())
            if self.family == "mysql":
                self.take(") AS ")
                self.identifier("b")
            self.take(")")
        if statement.kind != "data":
            self.take(", ")
            self.cte(prefix + "guards", guards)
            self.take("SELECT ")
            for i, subject in enumerate(statement.subjects):
                if i:
                    self.take(", ")
                self.take("CAST(CASE WHEN EXISTS (SELECT 1 FROM ")
                self.relation(subject.inputs[0])
                self.take(" WHERE EXISTS (SELECT 1 FROM ")
                self.relation(subject.inputs[1])
                self.take(" WHERE ")
                self.match(subject.unit)
                self.take(" LIMIT ")
                self.control(statement.controls[0])
                self.take(" OFFSET ")
                self.control(statement.controls[1])
                self.take(
                    ")) THEN 1 ELSE 0 END"
                    + (" AS BIGINT)" if self.family == "postgres" else " AS SIGNED)")
                )
                self.take(" AS ")
                self.identifier(guards[i])
            self.take(")")
        if statement.kind == "guard":
            self.take(" SELECT ")
            self.names(guards)
            self.take(" FROM ")
            self.identifier(prefix + "guards")
        elif statement.kind == "combined":
            self.take(", ")
            self.cte(prefix + "wire", (channel,) + guards + data_fields)
            self.take("SELECT ")
            self.integer(0)
            for name in guards:
                self.take(", ")
                self.column("g", name)
            for _ in data_fields:
                self.take(", NULL")
            self.take(" FROM ")
            self.identifier(prefix + "guards")
            self.take(" AS ")
            self.identifier("g")
            self.take(" UNION ALL SELECT ")
            self.integer(1)
            for name in guards:
                self.take(", ")
                self.column("g", name)
            for name in data_fields:
                self.take(", ")
                self.column("d", name)
            self.take(" FROM ")
            self.identifier(prefix + "guards")
            self.take(" AS ")
            self.identifier("g")
            self.take(" CROSS JOIN ")
            self.identifier(prefix + "data")
            self.take(" AS ")
            self.identifier("d")
            self.take(" WHERE ")
            for i, name in enumerate(guards):
                if i:
                    self.take(" AND ")
                self.column("g", name)
                self.take(" = 0")
            self.take(") SELECT ")
            self.identifier(channel)
            for name in guards:
                self.take(", ")
                self.identifier(name)
            for name, column in zip(public, p.output.columns, strict=True):
                self.take(", ")
                self.identifier(name)
                self.take(" AS ")
                self.identifier(column.label)
            for name, _alias, _column in extra:
                self.take(", ")
                self.identifier(name)
            self.take(" FROM ")
            self.identifier(prefix + "wire")
            self.take(" ORDER BY ")
            self.identifier(channel)
            self.take(" ASC")
            for name, direction in ordering:
                self.take(", ")
                self.identifier(name)
                self.take(" " + direction.upper())
        else:
            self.take(" SELECT ")
            for i, (name, column) in enumerate(
                zip(public, p.output.columns, strict=True)
            ):
                if i:
                    self.take(", ")
                self.identifier(name)
                self.take(" AS ")
                self.identifier(column.label)
            self.take(" FROM ")
            self.identifier(prefix + "data")
            if ordering:
                self.take(" ORDER BY ")
                for i, (name, direction) in enumerate(ordering):
                    if i:
                        self.take(", ")
                    self.identifier(name)
                    self.take(" " + direction.upper())
        self.finish()

    def finish(self):
        need(
            self.position == len(self.text) and len(self.uses) == len(self.native.uses),
            "NATIVE_COVERAGE",
        )
        if self.family == "postgres":
            arguments = {}
            for _domain, _owner, index, value in self.uses:
                arguments[index] = value
            need(
                sorted(arguments) == list(range(1, len(arguments) + 1)), "PARAMETER_GAP"
            )
            expected = tuple(arguments[i] for i in range(1, len(arguments) + 1))
        else:
            expected = tuple(use[3] for use in self.uses)
        need(
            len(expected) == len(self.native.arguments)
            and all(
                same_value(a, b)
                for a, b in zip(expected, self.native.arguments, strict=True)
            ),
            "NATIVE_ARGUMENTS",
        )


def verify_native_guard(native):
    need(
        type(native) is NativeGuardStatement
        and type(native.sql) is bytes
        and type(native.uses) is tuple
        and type(native.arguments) is tuple,
        "NATIVE_ROOT",
    )
    verify_statement(native.statement)
    limits = resource_limits(native.statement.program.preparation.artifact.request)
    need(
        len(native.sql) <= limits["sql_bytes"]
        and len(native.uses) <= limits["parameters"],
        "RESOURCE_LIMIT",
    )
    if native.statement.kind == "data" and not native.statement.subjects:
        from pietto._project.project_execution_binding_verification import (
            native_arguments,
        )

        artifact = native.statement.program.preparation.artifact
        need(
            native.sql == artifact.rendered.sql
            and len(native.uses) == len(artifact.parameter_uses),
            "ORIGINAL_DATA_CORRESPONDENCE",
        )
        expected = native_arguments(
            artifact,
            tuple(
                s.site.position.literal.value
                for s in artifact.request.plan.literal_slots
            ),
        )
        for actual, original in zip(native.uses, artifact.parameter_uses, strict=True):
            need(
                type(actual) is GuardParameterUse
                and actual.domain == "original"
                and actual.owner is original.slot
                and actual.original is original
                and type(actual.index) is int
                and actual.index == original.server_index
                and same_value(actual.value, expected[original.server_index - 1]),
                "ORIGINAL_PARAMETER_CORRESPONDENCE",
            )
        need(
            len(native.arguments) == len(expected)
            and all(
                same_value(a, b)
                for a, b in zip(native.arguments, expected, strict=True)
            ),
            "NATIVE_ARGUMENTS",
        )
        return
    _Read(native).run()
