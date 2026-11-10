"""Raw S04/S05 stats campaign plan, future driver and independent judge.

No database work happens unless the future owner passes --run explicitly.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path
import random
import re
from typing import Any


EPSILON = Decimal(2) ** -52
TABLE_PATTERN = re.compile(r"^p77_stats_[a-z0-9_]+$")
STAT_FUNCTIONS = ("stddev", "variance", "pvariance", "pstdev")
SUM_AVG_FUNCTIONS = ("sum", "avg")


@dataclass(frozen=True, slots=True)
class Cell:
    name: str
    kind: str
    values: tuple[int | float | None, ...]
    terminal_statistics: bool = False
    sum_must_terminal: bool = False
    avg_may_terminal: bool = False


def _seeded_ints() -> tuple[int, ...]:
    rng = random.Random(72)
    return tuple(rng.randint(-(10**6), 10**6) for _ in range(10_000))


INT_CELLS = (
    Cell("I0", "Int", ()),
    Cell("I1", "Int", (7,)),
    Cell("I1N", "Int", (7, None, None)),
    Cell("IN", "Int", (None, None)),
    Cell("I2", "Int", (1, 2)),
    Cell("M8", "Int", (2, 4, 4, 4, 5, 5, 7, 9)),
    Cell("I53", "Int", tuple((1 << 53) + offset for offset in (1, 3, 5))),
    Cell("I64", "Int", (-(1 << 63), (1 << 63) - 1)),
    Cell("IS", "Int", (0, 100_000_000)),
    Cell("IN10K", "Int", _seeded_ints()),
)
FLOAT_CELLS = (
    Cell("F0", "Float", ()),
    Cell("FN", "Float", (None, None)),
    Cell("F1", "Float", (1.5,)),
    Cell("F2", "Float", (1.0, 2.0)),
    Cell("F3", "Float", (0.1, 0.2, 0.3)),
    Cell("FZ", "Float", (-0.0, 0.0)),
    Cell("FO", "Float", (1e9 + 0.1, 1e9 + 0.1, 1e9 + 0.1, 1e9 + 0.2)),
    Cell("FL", "Float", (1e150, 3e150, 5e150)),
    Cell("FT", "Float", (1e-300, 3e-300, 5e-300)),
    Cell("FOVER_SUM", "Float", (1.7e308, 1.7e308), sum_must_terminal=True, avg_may_terminal=True),
    Cell("O1", "Float", (1e200, -1e200)),
    Cell("O2", "Float", (1.7e308, -1.7e308), terminal_statistics=True),
)


def encoded_value(value: int | float | None) -> int | str | None:
    if value is None or type(value) is int:
        return value
    if type(value) is float:
        return value.hex()
    raise TypeError("seed value")


def encoded_result(value: object) -> object:
    if type(value) is float:
        return value.hex()
    if value is None or type(value) in {int, str, bool}:
        return value
    if type(value) is Decimal:
        return {"decimal": format(value, "f")}
    return {"type": type(value).__name__, "repr": repr(value)}


def decoded_value(value: int | str | None, kind: str) -> int | float | None:
    if value is None:
        return None
    if kind == "Int" and type(value) is int:
        return value
    if kind == "Float" and type(value) is str:
        return float.fromhex(value)
    raise ValueError("seed encoding")


def cell_by_name(name: str) -> Cell:
    for cell in (*INT_CELLS, *FLOAT_CELLS):
        if cell.name == name:
            return cell
    raise ValueError("unknown cell")


def sql(engine: str, function: str, kind: str, table: str) -> tuple[str, str, str, str]:
    if engine not in {"postgres", "mysql"} or function not in {
        *STAT_FUNCTIONS,
        *SUM_AVG_FUNCTIONS,
    }:
        raise ValueError("engine/function")
    if not TABLE_PATTERN.fullmatch(table):
        raise ValueError("owned table name")
    if engine == "postgres":
        quote, placeholder, field = '"', "%s", "DOUBLE PRECISION" if kind == "Float" else "BIGINT"
        table_name = f'{quote}{table}{quote}'
        value = '"value"'
    else:
        quote, placeholder, field = "`", "%s", "DOUBLE" if kind == "Float" else "BIGINT"
        table_name = f'{quote}{table}{quote}'
        value = "`value`"
    create = f"CREATE TABLE {table_name} ({quote}ordinal{quote} INTEGER NOT NULL, {value} {field} NULL)"
    insert = f"INSERT INTO {table_name} ({quote}ordinal{quote}, {value}) VALUES ({placeholder}, {placeholder})"
    readback = f"SELECT {quote}ordinal{quote}, {value} FROM {table_name} ORDER BY {quote}ordinal{quote}"
    if engine == "postgres" and kind == "Int" and function in STAT_FUNCTIONS:
        expression = {
            "stddev": f"SQRT(CAST(VAR_SAMP({value}) AS double precision))",
            "variance": f"CAST(VAR_SAMP({value}) AS double precision)",
            "pvariance": f"CAST(VAR_POP({value}) AS double precision)",
            "pstdev": f"SQRT(CAST(VAR_POP({value}) AS double precision))",
        }[function]
    else:
        argument = value if kind == "Float" or engine == "postgres" else f"CAST({value} AS DECIMAL(65,0))"
        expression = {
            "sum": f"SUM({value})",
            "avg": f"AVG({value})",
            "stddev": f"STDDEV_SAMP({argument})",
            "variance": f"VAR_SAMP({argument})",
            "pvariance": f"VAR_POP({argument})",
            "pstdev": f"STDDEV_POP({argument})",
        }[function]
    return create, insert, readback, f"SELECT {expression} AS {quote}result{quote} FROM {table_name}"


def _present(cell: Cell) -> list[Decimal]:
    return [
        Decimal(value) if cell.kind == "Int" else Decimal.from_float(value)
        for value in cell.values
        if value is not None
    ]


def _variance(values: list[Decimal], population: bool) -> Decimal | None:
    if not values or (not population and len(values) < 2):
        return None
    with localcontext() as context:
        context.prec = 1300
        mean = sum(values) / Decimal(len(values))
        return sum((value - mean) ** 2 for value in values) / Decimal(
            len(values) if population else len(values) - 1
        )


def statistic_truth(cell: Cell, function: str) -> Decimal | None:
    values = _present(cell)
    population = function in {"pvariance", "pstdev"}
    variance = _variance(values, population)
    if variance is None:
        return None
    if function in {"variance", "pvariance"}:
        return variance
    with localcontext() as context:
        context.prec = 1300
        return variance.sqrt()


def statistic_bound(cell: Cell, function: str, truth: Decimal) -> Decimal:
    if truth == 0:
        return Decimal(0)
    if cell.kind == "Int":
        return (EPSILON if function in {"variance", "pvariance"} else 2 * EPSILON) * truth
    values = _present(cell)
    count = len(values)
    with localcontext() as context:
        context.prec = 1300
        denominator = count if function in {"pvariance", "pstdev"} else count - 1
        rms = (sum(value * value for value in values) / Decimal(denominator)).sqrt()
        deviation = truth if function in {"stddev", "pstdev"} else truth.sqrt()
        deviation_bound = 4 * EPSILON * deviation + 8 * count * EPSILON * rms + 2 * (Decimal(count) * (Decimal(2) ** -1074)).sqrt()
        return deviation_bound if function in {"stddev", "pstdev"} else 2 * deviation * deviation_bound


def _float_value(value: object) -> float:
    if type(value) is str:
        value = float.fromhex(value)
    if type(value) is not float or not math.isfinite(value):
        raise ValueError("finite binary64 result required")
    return value


def _metadata(value: object) -> list[dict[str, object]]:
    if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
        raise ValueError("one result metadata record required")
    item = value[0]
    if "type_code" not in item or "flags" not in item or item["type_code"] is None:
        raise ValueError("result metadata incomplete")
    return value


def _seed_readback(cell: Cell, value: object) -> None:
    if type(value) is not list or len(value) != len(cell.values):
        raise ValueError("seed readback cardinality")
    expected = [encoded_value(item) for item in cell.values]
    actual = []
    for ordinal, item in enumerate(value):
        if type(item) is not dict or item.get("ordinal") != ordinal or "value" not in item:
            raise ValueError("seed readback shape")
        decoded = decoded_value(item["value"], cell.kind)
        actual.append(encoded_value(decoded))
    if actual != expected:
        raise ValueError("seed readback identity")


def validate(record: object) -> str:
    if type(record) is not dict:
        raise ValueError("record object")
    required = {"engine", "function", "case", "table", "seed", "sql", "params", "seed_readback", "metadata", "warnings", "outcome"}
    if set(record) != required:
        raise ValueError("record keys")
    engine, function = record["engine"], record["function"]
    if engine not in {"postgres", "mysql"} or function not in {*STAT_FUNCTIONS, *SUM_AVG_FUNCTIONS}:
        raise ValueError("record engine/function")
    cell = cell_by_name(str(record["case"]))
    if record["seed"] != [encoded_value(value) for value in cell.values]:
        raise ValueError("seed record")
    if type(record["table"]) is not str or type(record["params"]) is not list:
        raise ValueError("sql/params")
    _, _, _, expected_sql = sql(str(engine), str(function), cell.kind, record["table"])
    if record["sql"] != expected_sql or record["params"] != []:
        raise ValueError("planned SQL/params identity")
    if type(record["warnings"]) is not list:
        raise ValueError("warnings required")
    if record["warnings"]:
        raise ValueError("warning-only conversion rejected")
    _seed_readback(cell, record["seed_readback"])
    outcome = record["outcome"]
    if type(outcome) is not dict or set(outcome) != {"status", "rows", "error"}:
        raise ValueError("outcome shape")
    if outcome["status"] == "error":
        if outcome["rows"] != [] or type(outcome["error"]) is not dict:
            raise ValueError("terminal error must have no rows and an error record")
        if not any(outcome["error"].get(key) is not None for key in ("sqlstate", "errno", "message")):
            raise ValueError("terminal error identity")
        if cell.terminal_statistics and function in STAT_FUNCTIONS:
            return "terminal-observed"
        if cell.sum_must_terminal and function == "sum":
            return "terminal-observed"
        if cell.avg_may_terminal and function == "avg":
            return "raw-avg-terminal-observed"
        raise ValueError("unexpected terminal error")
    if outcome["status"] != "row" or outcome["error"] is not None:
        raise ValueError("row outcome")
    metadata = _metadata(record["metadata"])
    expected_type_code = 701 if engine == "postgres" else (5 if cell.kind == "Float" else None)
    if expected_type_code is not None and metadata[0]["type_code"] != expected_type_code:
        raise ValueError("result carrier metadata")
    rows = outcome["rows"]
    if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not list or len(rows[0]) != 1:
        raise ValueError("single aggregate row")
    observed = rows[0][0]
    if function in SUM_AVG_FUNCTIONS:
        if not _present(cell):
            if observed is not None:
                raise ValueError("sum/avg NULL shape")
            return "raw-null-observed"
        _float_value(observed)
        if cell.sum_must_terminal and function == "sum":
            raise ValueError("sum overflow must terminate")
        if cell.avg_may_terminal and function == "avg":
            return "raw-avg-finite-observed"
        return "raw-bits-observed"
    truth = statistic_truth(cell, function)
    if truth is None:
        if observed is not None:
            raise ValueError("statistic NULL shape")
        return "raw-statistic-null"
    observed_float = _float_value(observed)
    observed_decimal = Decimal.from_float(observed_float)
    if truth == 0:
        if observed_float != 0.0:
            raise ValueError("exact zero statistic")
        return "raw-statistic-zero"
    if cell.kind == "Float" and (
        (function in {"variance", "pvariance"} and truth < Decimal("1e-322"))
        or (function in {"stddev", "pstdev"} and truth < Decimal("1e-161"))
    ) and observed_float == 0.0:
        return "raw-statistic-underflow-observed"
    if abs(observed_decimal - truth) > statistic_bound(cell, function, truth):
        raise ValueError("statistic spread bound")
    return "raw-statistic-within-contract-bound"


def _description(item: object) -> dict[str, object]:
    if hasattr(item, "name"):
        return {"name": item.name, "type_code": getattr(item, "type_code", None), "flags": getattr(item, "flags", None)}
    if type(item) is tuple and len(item) >= 2:
        return {"name": item[0], "type_code": item[1], "flags": item[7] if len(item) > 7 else None}
    raise ValueError("driver description")


def _warnings(connection: object, engine: str) -> list[dict[str, object]]:
    if engine == "postgres":
        return []
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW WARNINGS")
        return [
            {"level": row[0], "code": row[1], "message": row[2]}
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()


def _captured_warnings(connection: object, engine: str) -> list[dict[str, object]]:
    try:
        return _warnings(connection, engine)
    except Exception as error:
        return [{"capture_error": type(error).__name__}]


def _connect(engine: str, endpoint: dict[str, object]):
    if engine == "postgres":
        import psycopg

        return psycopg.connect(str(endpoint["dsn"]))
    import mysql.connector

    return mysql.connector.connect(**endpoint)


def run(engine: str, endpoint_path: Path, table: str, output: Path) -> None:
    endpoint = json.loads(endpoint_path.read_text(encoding="utf-8"))
    if type(endpoint) is not dict:
        raise ValueError("endpoint object")
    if output.exists():
        raise ValueError("owned output directory already exists")
    output.mkdir(mode=0o700, parents=True)
    connection = _connect(engine, endpoint)
    try:
        for cell in (*INT_CELLS, *FLOAT_CELLS):
            for function in (*STAT_FUNCTIONS, *SUM_AVG_FUNCTIONS):
                if cell.kind == "Int" and function in SUM_AVG_FUNCTIONS:
                    continue
                if cell.terminal_statistics and function in SUM_AVG_FUNCTIONS:
                    continue
                if (cell.sum_must_terminal or cell.avg_may_terminal) and function in STAT_FUNCTIONS:
                    continue
                create, insert, readback, statement = sql(engine, function, cell.kind, table)
                cursor = connection.cursor()
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {'`' if engine == 'mysql' else chr(34)}{table}{'`' if engine == 'mysql' else chr(34)}")
                    cursor.execute(create)
                    for ordinal, value in enumerate(cell.values):
                        cursor.execute(insert, (ordinal, value))
                    cursor.execute(readback)
                    seed_readback = [
                        {"ordinal": row[0], "value": encoded_value(row[1])}
                        for row in cursor.fetchall()
                    ]
                    cursor.execute(statement)
                    rows = [[encoded_result(value) for value in row] for row in cursor.fetchall()]
                    record = {
                        "engine": engine,
                        "function": function,
                        "case": cell.name,
                        "table": table,
                        "seed": [encoded_value(value) for value in cell.values],
                        "sql": statement,
                        "params": [],
                        "seed_readback": seed_readback,
                        "metadata": [_description(item) for item in cursor.description],
                        "warnings": _captured_warnings(connection, engine),
                        "outcome": {"status": "row", "rows": rows, "error": None},
                    }
                except Exception as error:
                    record = {
                        "engine": engine,
                        "function": function,
                        "case": cell.name,
                        "table": table,
                        "seed": [encoded_value(value) for value in cell.values],
                        "sql": statement,
                        "params": [],
                        "seed_readback": [],
                        "metadata": [],
                        "warnings": _captured_warnings(connection, engine),
                        "outcome": {
                            "status": "error",
                            "rows": [],
                            "error": {"sqlstate": getattr(error, "sqlstate", None), "errno": getattr(error, "errno", None), "message": type(error).__name__},
                        },
                    }
                finally:
                    cursor.close()
                try:
                    record["judge"] = {"status": "RAW_OBSERVATION", "result": validate(record)}
                except ValueError as error:
                    record["judge"] = {"status": "REJECTED", "reason": str(error)}
                (output / f"{engine}-{function}-{cell.name}.json").write_text(
                    json.dumps(record, sort_keys=True) + "\n", encoding="utf-8"
                )
    finally:
        try:
            cursor = connection.cursor()
            try:
                quote = "`" if engine == "mysql" else '"'
                cursor.execute(f"DROP TABLE IF EXISTS {quote}{table}{quote}")
            finally:
                cursor.close()
        finally:
            connection.close()


def _record(cell: Cell, function: str, value: object) -> dict[str, object]:
    table = "p77_stats_selfcheck"
    _, _, _, statement = sql("postgres", function, cell.kind, table)
    return {
        "engine": "postgres",
        "function": function,
        "case": cell.name,
        "table": table,
        "seed": [encoded_value(item) for item in cell.values],
        "sql": statement,
        "params": [],
        "seed_readback": [{"ordinal": index, "value": encoded_value(item)} for index, item in enumerate(cell.values)],
        "metadata": [{"name": "result", "type_code": 701, "flags": None}],
        "warnings": [],
        "outcome": {"status": "row", "rows": [[value]], "error": None},
    }


def _reject(record: dict[str, object]) -> None:
    try:
        validate(record)
    except ValueError:
        return
    raise AssertionError("malformed record was accepted")


def selfcheck() -> None:
    _reject(None)  # type: ignore[arg-type]
    int_cell = cell_by_name("I2")
    int_truth = statistic_truth(int_cell, "variance")
    assert int_truth is not None
    good = _record(int_cell, "variance", float(int_truth))
    assert validate(good) == "raw-statistic-within-contract-bound"
    wrong_sql = dict(good)
    wrong_sql["sql"] = "SELECT wrong"
    _reject(wrong_sql)
    missing_warnings = dict(good)
    missing_warnings.pop("warnings")
    _reject(missing_warnings)
    missing_metadata = dict(good)
    missing_metadata["metadata"] = []
    _reject(missing_metadata)
    wrong_metadata = dict(good)
    wrong_metadata["metadata"] = [{"name": "result", "type_code": 0, "flags": None}]
    _reject(wrong_metadata)
    wrong_arity = dict(good)
    wrong_arity["outcome"] = {"status": "row", "rows": [[1.0, 2.0]], "error": None}
    _reject(wrong_arity)
    wrong_null = _record(cell_by_name("F0"), "sum", 0.0)
    _reject(wrong_null)
    for invalid in (math.nan, math.inf, -math.inf):
        _reject(_record(cell_by_name("F3"), "sum", invalid))
    _reject(_record(int_cell, "variance", 100.0))
    _reject(_record(cell_by_name("FOVER_SUM"), "sum", 1.7e308))
    assert validate(_record(cell_by_name("FOVER_SUM"), "avg", 1.7e308)) == "raw-avg-finite-observed"
    f2 = cell_by_name("F2")
    pvariance = statistic_truth(f2, "pvariance")
    variance = statistic_truth(f2, "variance")
    assert pvariance is not None and variance is not None
    assert statistic_bound(f2, "pvariance", pvariance) != statistic_bound(f2, "variance", variance)
    terminal = _record(cell_by_name("FOVER_SUM"), "sum", None)
    terminal["outcome"] = {"status": "error", "rows": [], "error": {"sqlstate": "22003", "errno": None, "message": "overflow"}}
    assert validate(terminal) == "terminal-observed"
    terminal["outcome"] = {"status": "error", "rows": [[1.0]], "error": {"sqlstate": "22003", "errno": None, "message": "overflow"}}
    _reject(terminal)
    print("selfcheck: pass")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selfcheck", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--engine", choices=("postgres", "mysql"))
    parser.add_argument("--endpoint", type=Path)
    parser.add_argument("--table")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.selfcheck:
        selfcheck()
        return 0
    if not args.run or not all((args.engine, args.endpoint, args.table, args.output)):
        parser.error("--run --engine --endpoint --table --output are required for a future DB run")
    run(args.engine, args.endpoint, args.table, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
