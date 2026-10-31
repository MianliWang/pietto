"""Exact public outputs of a verified complete emission, without source fiction.

The emission verifier independently checks expression, use, terminal and target
realization laws. This view retains those actual nodes; it is not another
semantic evaluator. Verification never calls the view's constructor.
"""

from dataclasses import dataclass, field as dc_field
from typing import Any

from pietto._project.project_result_contract import (
    NestedShape,
    ResultError,
    build_result_contract,
    scalar_fields,
    verify_result_contract,
)
from pietto._project.project_sql_emission_ast import (
    SQLColumn,
    SQLLiteralColumn,
    SQLSelect,
    SQLRowQuery,
    CompiledSQLQuery,
    SQLJoinQuery,
    RowValueColumn,
    RowCarryColumn,
)
from pietto._project.project_sql_emission_aggregation import AggregateProjectionColumn
from pietto._project.project_sql_emission_windows import WindowProjectionColumn
from pietto._project.project_sql_emission_results import (
    ResultColumn,
    ResultGroupColumn,
)
from pietto._project.project_sql_emission_nested import CollectColumn
from pietto._project.project_sql_emission_sets import SetColumn
from pietto._project.project_sql_emission_values import ValuesOutputColumn
from pietto._project.project_sql_emission_rows import (
    Realization,
    field_realization,
    constant_realization,
)
from pietto._project.project_sql_emission_inspection import inspect_project_sql_emission
from pietto._project.project_verification_scope import entry

__all__: tuple[str, ...] = ()
# The one PostgreSQL carrier of a collected field (S02): a count, then one
# array per child field in child order, all aligned by the child sequence.
PG_COLUMN_ARRAYS_V1 = "pg_column_arrays_v1"


@dataclass(frozen=True, slots=True, eq=False)
class OutputColumn:
    original: Any = dc_field(repr=False)
    field: Any = dc_field(repr=False)
    ordinal: int
    label: str
    export: Any = dc_field(repr=False)
    terminal: Any = dc_field(repr=False)
    realization: Realization = dc_field(repr=False)
    source_field: Any = dc_field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class NestedOutputColumn:
    """One collected field and its carrier descriptor, never a scalar output.

    ``original`` is the statement's Collect column (or the result body's
    carried group of it). The statement returns ``aliases``: the count, then
    one array per child in child order; ``children`` are the collected
    terminal's own outputs, one per child leaf of ``field``.
    """

    original: Any = dc_field(repr=False)
    field: Any = dc_field(repr=False)
    ordinal: int
    label: str
    export: Any = dc_field(repr=False)
    terminal: Any = dc_field(repr=False)
    carrier: str
    aliases: tuple[str, ...]
    children: tuple[OutputColumn, ...] = dc_field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class GeneralOutput:
    artifact: Any = dc_field(repr=False)
    contract: Any = dc_field(repr=False)
    binding: Any = dc_field(repr=False)
    units: tuple[Any, ...] = dc_field(repr=False)
    # An OutputColumn per field, a NestedOutputColumn for a collected one.
    columns: tuple[Any, ...] = dc_field(repr=False)
    guarded: Any = dc_field(default=None, repr=False)


@entry
def prepare_output(artifact, *, binding=None):
    return _prepare_output(artifact, binding=binding)


def _inspect_output(artifact, guarded):
    if guarded is None:
        return inspect_project_sql_emission(artifact, artifact.request)
    from pietto._project.project_guard_preparation import inspect_pending

    return inspect_pending(guarded, artifact)


def _prepare_output(artifact, *, binding=None, guarded=None):
    # A pending output is structural correspondence, never SQL execution permission.
    view = _inspect_output(artifact, guarded)
    contract = build_result_contract(
        view.request.verification, scalar_meaning=view.request.scalar_meaning
    )
    ast = artifact.ast
    if type(ast) is SQLSelect:
        units = tuple(c.body for c in ast.ctes) + (ast,)
    elif type(ast) in (SQLRowQuery, CompiledSQLQuery):
        units = ast.bodies
    elif type(ast) is SQLJoinQuery:
        units = ast.units
    else:
        raise ResultError("OUTPUT_ROOT")
    if guarded is not None:
        scalar_fields(contract)
    columns: list[OutputColumn | NestedOutputColumn] = []
    for original, leaf in zip(view.columns, contract.shape.fields, strict=True):
        if type(leaf.shape) is NestedShape:
            columns.append(_nested_column(original, leaf, units[-1]))
            continue
        if type(original) is SQLColumn:
            source = original.source_field
            realized = field_realization(source)
        elif type(original) is SQLLiteralColumn:
            # A named literal reads its retained producer's actual value.
            value = original.value
            if value is None:
                value = original.origin.value
            realized = constant_realization(value, view.request.family)
            source = None
        else:
            realized = original.column.realization
            source = original.column.field
        if realized is None:
            raise ResultError("OUTPUT_REALIZATION")
        columns.append(
            OutputColumn(
                original,
                leaf,
                original.ordinal,
                original.label,
                original.export,
                units[-1],
                realized,
                source,
            )
        )
    output = GeneralOutput(artifact, contract, binding, units, tuple(columns), guarded)
    verify_output(output, artifact, contract, binding=binding)
    return output


def _group(original):
    """The Collect column a final statement column carries, or None."""
    if type(original) is ResultGroupColumn:
        original = original.group
    return original if type(original) is CollectColumn else None


def _nested_column(original, leaf, terminal):
    group = _group(original)
    if group is None:
        raise ResultError("OUTPUT_COLUMNS")
    body = group.lateral.target.producer
    if len(body.columns) != len(leaf.shape.fields):
        raise ResultError("OUTPUT_CARRIER")
    return NestedOutputColumn(
        original,
        leaf,
        original.ordinal,
        original.label,
        original.export,
        terminal,
        PG_COLUMN_ARRAYS_V1,
        tuple(carrier[1] for carrier in original.carriers),
        tuple(
            OutputColumn(
                column,
                child,
                k,
                child.label,
                column.export,
                body,
                column.column.realization,
                column.column.field,
            )
            for k, (column, child) in enumerate(
                zip(body.columns, leaf.shape.fields, strict=True)
            )
        ),
    )


@entry
def verify_output(output, artifact, contract, *, binding=None):
    if (
        type(output) is not GeneralOutput
        or output.artifact is not artifact
        or output.contract is not contract
        or output.binding is not binding
    ):
        raise ResultError("OUTPUT_ROOT")
    if output.guarded is not None:
        # A guarded program reads scalar leaves only until S12/S20 open it.
        scalar_fields(contract)
    if binding is not None:
        from pietto._project.project_execution_binding_verification import (
            verify_binding,
        )

        verify_binding(binding)
        if binding.artifact is not artifact or binding.guarded is not output.guarded:
            raise ResultError("OUTPUT_BINDING")
    # This upstream verifier independently re-derives all concrete realizations,
    # including hidden computations and both complete SEMI/ANTI input terminals;
    # its compiled and guarded checks run once per top-level call for these
    # exact objects.
    view = _inspect_output(artifact, output.guarded)
    verify_result_contract(contract, view.request.verification)
    if contract.scalar_meaning is not view.request.scalar_meaning:
        raise ResultError("OUTPUT_MEANING")
    leaves = contract.shape.fields
    ast = artifact.ast
    if type(ast) is SQLSelect:
        expected_units = tuple(c.body for c in ast.ctes) + (ast,)
    elif type(ast) in (SQLRowQuery, CompiledSQLQuery):
        expected_units = ast.bodies
    elif type(ast) is SQLJoinQuery:
        expected_units = ast.units
    else:
        raise ResultError("OUTPUT_TERMINAL")
    if (
        type(output.units) is not tuple
        or len(output.units) != len(expected_units)
        or any(a is not b for a, b in zip(output.units, expected_units, strict=True))
        or type(output.columns) is not tuple
        or len(output.columns) != len(leaves)
        or len(view.columns) != len(output.columns)
    ):
        raise ResultError("OUTPUT_INVENTORY")
    for ordinal, (supplied, original, leaf) in enumerate(
        zip(output.columns, view.columns, leaves, strict=True)
    ):
        nested = type(leaf.shape) is NestedShape
        if (
            type(supplied) is not (NestedOutputColumn if nested else OutputColumn)
            or supplied.original is not original
            or supplied.field is not leaf
            or supplied.export is not leaf.port
            or original.export is not leaf.port
            or type(supplied.ordinal) is not int
            or supplied.ordinal != ordinal
            or original.ordinal != ordinal
            or type(supplied.label) is not str
            or supplied.label != leaf.label
            or original.label != leaf.label
            or supplied.terminal is not expected_units[-1]
        ):
            raise ResultError("OUTPUT_COLUMNS")
        if isinstance(supplied, NestedOutputColumn):  # exact type checked above
            _verify_nested(supplied, original, leaf, view.request.family)
            continue
        if type(original) is SQLColumn:
            expected = field_realization(original.source_field)
            source = original.source_field
        elif type(original) is SQLLiteralColumn:
            value = (
                original.value if original.value is not None else original.origin.value
            )
            expected = constant_realization(value, view.request.family)
            source = None
        elif type(original) in (
            RowValueColumn,
            RowCarryColumn,
            AggregateProjectionColumn,
            WindowProjectionColumn,
            ResultColumn,
            SetColumn,
            ValuesOutputColumn,
        ):
            expected = original.column.realization
            source = original.column.field
            if supplied.realization is not expected:
                raise ResultError("OUTPUT_REALIZATION")
        else:
            raise ResultError("OUTPUT_COLUMNS")
        real = supplied.realization
        if (
            type(real) is not Realization
            or expected is None
            or real.tag != expected.tag
            or real.storage != expected.storage
            or real.domain != expected.domain
            or type(real.nullable) is not type(expected.nullable)
            or real.nullable != expected.nullable
            or supplied.source_field is not source
        ):
            raise ResultError("OUTPUT_REALIZATION")
    return output.columns


def _verify_nested(supplied, original, leaf, family):
    """The carrier descriptor of one collected field, re-derived from the
    statement's own Collect column and its collected terminal."""
    group = _group(original)
    if group is None or group.collect is not leaf.shape.collect:
        raise ResultError("OUTPUT_COLUMNS")
    body = group.lateral.target.producer
    leaves = leaf.shape.fields
    carriers = original.carriers
    if (
        family != "postgres"
        or type(supplied.carrier) is not str
        or supplied.carrier != PG_COLUMN_ARRAYS_V1
        or type(carriers) is not tuple
        or len(carriers) != 1 + len(leaves)
        or carriers[0][2] is not leaf.port.ref
        or len(group.collect.children) != len(leaves)
        or any(
            carrier[2] is not child
            for carrier, child in zip(carriers[1:], group.collect.children, strict=True)
        )
        or type(supplied.aliases) is not tuple
        or any(type(alias) is not str for alias in supplied.aliases)
        or supplied.aliases != tuple(carrier[1] for carrier in carriers)
        or type(supplied.children) is not tuple
        or len(supplied.children) != len(leaves)
        or len(body.columns) != len(leaves)
    ):
        raise ResultError("OUTPUT_CARRIER")
    for k, (child, column, child_leaf) in enumerate(
        zip(supplied.children, body.columns, leaves, strict=True)
    ):
        if (
            type(child) is not OutputColumn
            or type(column) is not ResultColumn
            or child.original is not column
            or child.field is not child_leaf
            or child.export is not child_leaf.port
            or column.export is not child_leaf.port
            or type(child.ordinal) is not int
            or child.ordinal != k
            or type(child.label) is not str
            or child.label != child_leaf.label
            or child.terminal is not body
        ):
            raise ResultError("OUTPUT_COLUMNS")
        if (
            type(child.realization) is not Realization
            or child.realization is not column.column.realization
            or child.source_field is not column.column.field
        ):
            raise ResultError("OUTPUT_REALIZATION")


def source_read_columns(output):
    """Physical columns actually read by the verified original statement.

    This is an observation of original typed references, not a resolver. A
    refinement must not acquire unused source-column privileges by projecting
    every declared field into its private source relation.
    """
    from pietto._project.project_sql_emission_ast import SQLScan, RowScan, RowBody
    from pietto._project.project_sql_emission_aggregation import (
        AggregateValueColumn,
        AggregateKeyColumn,
    )
    from pietto._project.project_sql_emission_windows import WindowColumn
    from pietto._project.project_sql_emission_joins import JoinBody
    from pietto._project.project_sql_emission_sets import SetBody
    from pietto._project.project_sql_emission_values import ValuesBody
    from pietto._project.project_sql_emission_rows import (
        SQLBlockRead,
        SQLStageReference,
        SQLOperation,
    )

    verify_output(output, output.artifact, output.contract, binding=output.binding)
    # R2 and guard source closures read scalar outputs only (S12/S20).
    scalar_fields(output.contract)
    sources = output.artifact.request.sources
    needed = {source: set() for source in sources}
    for unit in output.units:
        scopes = {}
        if type(unit) is JoinBody:
            for item in unit.inputs:
                if any(item.producer is source for source in sources):
                    scopes[item.symbol.name] = item.producer
        elif type(unit) is SetBody:
            for item in unit.operands:
                if any(item.producer is source for source in sources):
                    needed[item.producer].update(c.name for c in item.columns)
            continue
        elif type(unit) is ValuesBody:
            continue  # VALUES reads no physical column.
        elif type(unit.scan) in (SQLScan, RowScan):
            scopes[unit.scan.symbol.name] = unit.scan.realization
        # A row body over a relation still reads a source through a block read.
        if not scopes and type(unit) is not RowBody:
            continue

        def read(scope, name):
            if scope in scopes:
                needed[scopes[scope]].add(name)

        def expression(value, alias):
            if type(value) is SQLStageReference:
                read(
                    alias if value.scope is None else value.scope.name,
                    value.column.name,
                )
            elif type(value) is SQLOperation:
                for operand in value.operands:
                    expression(operand, alias)
            elif type(value) is SQLBlockRead:
                # Its operands and an `any` predicate read columns as a JOIN's
                # ON does, including the read source's own under its alias.
                producer = value.target.producer
                if any(producer is source for source in sources):
                    scopes[value.target.symbol.name] = producer
                for operand in value.operands:
                    expression(operand, alias)
                if value.predicate is not None:
                    expression(value.predicate, alias)

        if type(unit) is JoinBody:
            for column in unit.columns:
                read(column.scope.name, column.read.name)
            for equal in unit.equalities:
                read(equal.left_scope.name, equal.left.name)
                read(equal.right_scope.name, equal.right.name)
            if unit.predicate is not None:
                expression(unit.predicate, "")
            continue
        if type(unit) is SQLSelect:
            for column in unit.columns:
                if type(column) is SQLColumn:
                    read(unit.scan.symbol.name, column.symbol.name)
            continue
        if type(unit) is not RowBody:
            raise ResultError("OUTPUT_SOURCE_READ_UNIT")
        alias = unit.scan.symbol.name
        for column in unit.columns:
            if type(column) in (
                RowCarryColumn,
                AggregateKeyColumn,
                AggregateProjectionColumn,
                WindowProjectionColumn,
            ):
                read(alias, column.read.name)
            elif type(column) is RowValueColumn:
                expression(column.value, alias)
            elif type(column) is AggregateValueColumn:
                if column.argument is not None:
                    expression(column.argument, alias)
                if column.delimiter is not None:
                    expression(column.delimiter, alias)
                for order in column.order_by:
                    expression(order.value, alias)
            elif type(column) is WindowColumn:
                for argument in column.arguments:
                    if argument.read is not None:
                        read(alias, argument.read.name)
                for _, part in column.specification.partitions:
                    read(alias, part.name)
                for order in column.specification.orders:
                    read(alias, order.read.name)
            else:
                raise ResultError("OUTPUT_SOURCE_READ_COLUMN")
        if unit.predicate is not None:
            expression(unit.predicate.value, alias)
        if unit.aggregation is not None:
            for key in unit.aggregation.keys:
                read(alias, key.read.name)
    result = []
    for source in sources:
        columns = tuple(
            dict.fromkeys(f.column for f in source.fields if f.column in needed[source])
        )
        if set(columns) != needed[source]:
            raise ResultError("OUTPUT_SOURCE_READ_INVENTORY")
        result.append(columns)
    return tuple(result)
