import pytest

from _pietto_sql_aggregate_results import MATRIX_SHAPE, _compile
from pietto.ast_nodes import QueryDef, TableDef
from pietto.ir import AggregateCallIR, RelationIR
from pietto.semantic import EffectiveNullability
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


@pytest.mark.parametrize(
    "connector,emit",
    [("postgres.table", emit_postgres_sql), ("mysql.table", emit_mysql_sql)],
)
@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize(
    "expression,type_name,nullability,aggregates",
    [
        ("coalesce(sum(amount), 0)", "Int", EffectiveNullability.NON_NULL, 1),
        ("sum(amount) * 100 / count()", "Int", EffectiveNullability.UNKNOWN, 2),
        ("round(avg(price), 2)", "Decimal", EffectiveNullability.NULLABLE, 1),
        ("coalesce(sum(amount), count())", "Int", EffectiveNullability.NON_NULL, 2),
        ("sum(amount) + sum(amount)", "Int", EffectiveNullability.UNKNOWN, 2),
        ("count() + 1", "Int", EffectiveNullability.UNKNOWN, 1),
        ("count_distinct(customer_id) + 1", "Int", EffectiveNullability.UNKNOWN, 1),
        ("min(amount) + 1", "Int", EffectiveNullability.UNKNOWN, 1),
        ("year(min(created_at))", "Int", EffectiveNullability.NULLABLE, 1),
        ("round(stddev(score))", "Float", EffectiveNullability.NULLABLE, 1),
    ],
)
def test_scalar_aggregate_results_keep_types_and_every_leaf(
    connector, emit, grouped, expression, type_name, nullability, aggregates
):
    from pietto.ir.model import aggregate_composition_leaves

    source = MATRIX_SHAPE + f'source orders: Order = {connector}("orders")\n'
    source += "query q:\n    from orders\n"
    if grouped:
        source += "    group by status\n"
    source += f"    select value = {expression}\n"
    script, semantic, ir = _compile(source)
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    field = semantic.model.relation_row_schemas[relation].fields["value"]
    assert (field.resolved_type.name, field.nullability) == (type_name, nullability)
    relations = [
        definition
        for definition in ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    leaves = aggregate_composition_leaves(relations[0].projections[0].expression)
    assert leaves is not None
    calls = [leaf for leaf in leaves if isinstance(leaf, AggregateCallIR)]
    assert len(calls) == aggregates
    assert len({id(call) for call in calls}) == aggregates
    result = emit(ir)
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1


@pytest.mark.parametrize("key", ["amount", "amount + tax"])
def test_aggregate_composition_reads_the_exact_grouped_let_key(key):
    source = MATRIX_SHAPE + 'source orders: Order = postgres.table("orders")\n'
    source += f"query q:\n    from orders\n    let bucket = {key}\n    group by bucket\n    select value = bucket + coalesce(sum(amount), 0)\n    order by value\n"
    _, _, ir = _compile(source)
    result = emit_postgres_sql(ir)
    assert result.diagnostics == ()
    assert "GROUP BY" in result.artifacts[0].sql
