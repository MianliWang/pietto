import pytest

from pietto.errors import Severity
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


@pytest.mark.parametrize(
    "expression",
    [
        "sum(price * amount)",
        "sum(amount * price)",
        "sum(-price)",
        "sum(+price)",
        "price * amount",
        "amount * price",
        "price * 2",
        "2 * price",
        "-price",
        "+price",
    ],
)
@pytest.mark.parametrize("target", ["postgres", "mysql"])
def test_decimal_product_and_sign_emit_single_file(expression, target):
    source = (
        "shape Order:\n"
        "    price: Decimal\n"
        "    discount: Decimal\n"
        "    amount: Int\n"
        "    tax: Int\n"
        "    score: Float\n"
        "    status: Text\n"
        f'source orders: Order = {target}.table("orders")\n'
        f"table result:\n    from orders\n    select:\n        value = {expression}\n"
    )
    parsed = parse_source(source, path="phase42_decimal_int.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert [d.code for d in semantic.diagnostics if d.severity is Severity.ERROR] == []
    ir_result = build_ir(parsed.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    script_ir = ir_result.ir
    result = (emit_postgres_sql if target == "postgres" else emit_mysql_sql)(script_ir)
    assert result.diagnostics == ()
    assert "\n".join(artifact.sql for artifact in result.artifacts)
    quote = '"' if target == "postgres" else "`"
    price, amount = f"{quote}price{quote}", f"{quote}amount{quote}"
    scalar_sql = {
        "price * amount": f"{price} * {amount}",
        "amount * price": f"{amount} * {price}",
        "+price": f"+{price}",
        "-price": f"-{price}",
    }
    if expression in scalar_sql:
        assert (
            f"{scalar_sql[expression]} AS {quote}value{quote}"
            in result.artifacts[0].sql
        )
