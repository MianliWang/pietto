"""Pure judge for the Phase77 S15 MySQL signed-int primitive receipt.

It opens no connection and does not qualify a Pietto product form.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MIN_INT = -(1 << 63)
MAX_INT = (1 << 63) - 1
FORMAT = "pietto.phase77.s15.raw-receipt.v1"
ROUTES = ("literal", "physical_column", "prepared")
OPERATORS = ("/", "%")
SEED = (
    ("negative_dividend", -7, 2),
    ("negative_divisor", 7, -2),
    ("both_negative", -7, -2),
    ("null_left", None, 2),
    ("null_right", 7, None),
    ("zero_divisor", 7, 0),
    ("minimum_by_one", MIN_INT, 1),
    ("minimum_by_two", MIN_INT, 2),
    ("minimum_by_three", MIN_INT, 3),
    ("minimum_by_negative_one", MIN_INT, -1),
)


class ReceiptError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptError(message)


def _truncating_division(left: int, right: int) -> int:
    """Integer division toward zero; Python's // is intentionally not used."""
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


def expected_value(operator: str, left: int | None, right: int | None) -> int | None:
    if left is None or right is None or right == 0:
        return None
    if left == MIN_INT and right == -1:
        raise OverflowError("signed64 overflow is a native target terminal")
    quotient = _truncating_division(left, right)
    return quotient if operator == "/" else left - quotient * right


def _complete_warnings(terminal: dict[str, Any], where: str) -> list[Any]:
    warnings = terminal.get("warnings")
    _require(terminal.get("warnings_error") is False, f"{where}: warnings receipt failed")
    _require(isinstance(warnings, list), f"{where}: warnings must be raw list")
    for warning in warnings:
        _require(
            isinstance(warning, list)
            and len(warning) == 3
            and type(warning[0]) is str
            and type(warning[1]) is int
            and type(warning[2]) is str,
            f"{where}: warning is not a complete raw SHOW WARNINGS row",
        )
    return warnings


def _signed_bigint_metadata(metadata: Any, where: str) -> None:
    _require(isinstance(metadata, list) and len(metadata) == 1, f"{where}: exactly one value metadata column required")
    column = metadata[0]
    _require(isinstance(column, list) and len(column) == 9, f"{where}: raw Connector/Python metadata required")
    _require(type(column[0]) is str and type(column[1]) is int, f"{where}: malformed metadata")
    _require(column[1] == 8, f"{where}: result is not BIGINT")
    _require(type(column[7]) is int and not column[7] & 32, f"{where}: result is unsigned")


def _success(terminal: Any, value: int | None, *, allow_warnings: bool, where: str) -> None:
    _require(isinstance(terminal, dict) and terminal.get("kind") == "success", f"{where}: expected success")
    warnings = _complete_warnings(terminal, where)
    _require(allow_warnings or not warnings, f"{where}: safe/null cell has warning")
    _signed_bigint_metadata(terminal.get("metadata"), where)
    _require(terminal.get("rows") == [[value]], f"{where}: value differs from exact integer oracle")
    _require(terminal.get("errno") is None and terminal.get("sqlstate") is None, f"{where}: success has native error")


def _native_overflow(terminal: Any, where: str) -> None:
    _require(isinstance(terminal, dict) and terminal.get("kind") == "error", f"{where}: expected native overflow")
    _complete_warnings(terminal, where)
    _require(terminal.get("rows") == [] and terminal.get("metadata") is None, f"{where}: error carries result data")
    _require(terminal.get("errno") == 1690 and terminal.get("sqlstate") == "22003", f"{where}: expected native 1690/22003")
    _require(type(terminal.get("message")) is str and terminal["message"], f"{where}: native message missing")


def _seed_rows(seed: Any) -> None:
    expected = [
        {"ordinal": ordinal, "cell": cell, "left": left, "right": right}
        for ordinal, (cell, left, right) in enumerate(SEED)
    ]
    _require(seed == expected, "seed is not the frozen ordered signed-64 seed")


def _physical_seed(value: Any) -> None:
    _require(isinstance(value, dict), "physical_seed missing")
    _require(value.get("table") == "c77_s15_signed_operands", "physical seed table drift")
    _seed_rows(value.get("readback"))
    columns = value.get("show_columns")
    _require(isinstance(columns, list), "physical SHOW COLUMNS missing")
    by_name = {row[0]: row for row in columns if isinstance(row, list) and len(row) >= 2 and type(row[0]) is str}
    for name in ("left_value", "right_value"):
        row = by_name.get(name)
        _require(row is not None and type(row[1]) is str and row[1].lower() == "bigint", f"{name} is not signed BIGINT")
        _require("unsigned" not in row[1].lower(), f"{name} is unsigned")


def _sql_shape(observation: dict[str, Any], route: str, operator: str, left: int | None, right: int | None, where: str) -> None:
    statement = observation.get("statement")
    _require(isinstance(statement, dict) and type(statement.get("sql")) is str, f"{where}: SQL missing")
    sql = statement["sql"].upper()
    parameters = statement.get("parameters")
    _require(isinstance(parameters, list), f"{where}: raw parameter list missing")
    token = " DIV " if operator == "/" else " % "
    _require(token in f" {sql} ", f"{where}: wrong MySQL operator")
    if route == "literal":
        _require(parameters == [], f"{where}: literal route bound parameters")
        _require(statement.get("literal_operands") == [left, right], f"{where}: literal values differ from ordered seed")
        _require(sql.count(" AS SIGNED)") >= 2, f"{where}: literals are not explicitly signed")
    elif route == "physical_column":
        _require("LEFT_VALUE" in sql and "RIGHT_VALUE" in sql and "ORDINAL" in sql, f"{where}: physical column route drift")
        _require(parameters == [], f"{where}: physical operand route bound parameters")
    else:
        _require(sql.count("%S") >= 2 and sql.count(" AS SIGNED)") >= 2, f"{where}: prepared signed operands missing")
        _require(parameters == [left, right], f"{where}: prepared values differ from ordered seed")


def judge(receipt: Any) -> str:
    _require(isinstance(receipt, dict), "receipt must be an object")
    _require(receipt.get("format") == FORMAT, "receipt format mismatch")
    _require(receipt.get("engine") == "mysql", "S15 raw judge accepts only MySQL")
    _require(receipt.get("scope") == "raw_signed_int_primitive", "receipt claims product qualification")
    _require(receipt.get("signed_range") == {"min": MIN_INT, "max": MAX_INT}, "signed range missing or changed")
    _physical_seed(receipt.get("physical_seed"))
    observations = receipt.get("observations")
    _require(isinstance(observations, list), "observations missing")
    expected_count = len(OPERATORS) * len(ROUTES) * len(SEED)
    _require(len(observations) == expected_count, "observation matrix is incomplete")
    position = 0
    for operator in OPERATORS:
        for route in ROUTES:
            for ordinal, (cell, left, right) in enumerate(SEED):
                observation = observations[position]
                where = f"{operator}/{route}/{cell}"
                _require(isinstance(observation, dict), f"{where}: observation malformed")
                _require(
                    observation.get("operator") == operator
                    and observation.get("route") == route
                    and observation.get("ordinal") == ordinal
                    and observation.get("input") == {"left": left, "right": right},
                    f"{where}: observation order or inputs drift",
                )
                _sql_shape(observation, route, operator, left, right, where)
                try:
                    value = expected_value(operator, left, right)
                except OverflowError:
                    _native_overflow(observation.get("terminal"), where)
                else:
                    _success(
                        observation.get("terminal"),
                        value,
                        allow_warnings=right == 0,
                        where=where,
                    )
                position += 1
    return "S15_RAW_PRIMITIVE_MATCHED_NOT_PRODUCT_QUALIFIED"


def _metadata() -> list[list[Any]]:
    return [["value", 8, None, None, None, None, 1, 0, 63]]


def _signed_literal(value: int | None) -> str:
    return "NULL" if value is None else str(value)


def _synthetic_receipt() -> dict[str, Any]:
    observations = []
    for operator in OPERATORS:
        token = "DIV" if operator == "/" else "%"
        for route in ROUTES:
            for ordinal, (_, left, right) in enumerate(SEED):
                if route == "literal":
                    sql, parameters = f"SELECT CAST({_signed_literal(left)} AS SIGNED) {token} CAST({_signed_literal(right)} AS SIGNED) AS value", []
                elif route == "physical_column":
                    sql, parameters = f"SELECT left_value {token} right_value AS value FROM c77_s15_signed_operands WHERE ordinal = {ordinal}", []
                else:
                    sql, parameters = f"SELECT CAST(%s AS SIGNED) {token} CAST(%s AS SIGNED) AS value", [left, right]
                try:
                    value = expected_value(operator, left, right)
                    terminal: dict[str, Any] = {"kind": "success", "metadata": _metadata(), "rows": [[value]], "warnings": [], "warnings_error": False, "errno": None, "sqlstate": None}
                    if right == 0:
                        terminal["warnings"] = [["Warning", 1365, "Division by 0"]]
                except OverflowError:
                    terminal = {"kind": "error", "metadata": None, "rows": [], "warnings": [], "warnings_error": False, "errno": 1690, "sqlstate": "22003", "message": "BIGINT value is out of range"}
                statement = {"sql": sql, "parameters": parameters}
                if route == "literal":
                    statement["literal_operands"] = [left, right]
                observations.append({"operator": operator, "route": route, "ordinal": ordinal, "input": {"left": left, "right": right}, "statement": statement, "terminal": terminal})
    return {
        "format": FORMAT,
        "engine": "mysql",
        "scope": "raw_signed_int_primitive",
        "signed_range": {"min": MIN_INT, "max": MAX_INT},
        "physical_seed": {
            "table": "c77_s15_signed_operands",
            "show_columns": [["left_value", "bigint", "YES", "", None, ""], ["right_value", "bigint", "YES", "", None, ""]],
            "readback": [{"ordinal": ordinal, "cell": cell, "left": left, "right": right} for ordinal, (cell, left, right) in enumerate(SEED)],
        },
        "observations": observations,
    }


def self_check() -> None:
    receipt = _synthetic_receipt()
    assert judge(receipt) == "S15_RAW_PRIMITIVE_MATCHED_NOT_PRODUCT_QUALIFIED"
    for mutate in (
        lambda value: value["observations"].pop(),
        lambda value: value["observations"][0]["terminal"].update(metadata=[["value", 246, None, None, None, None, 1, 0, 63]]),
        lambda value: value["observations"][-1]["terminal"].update(errno=None),
        lambda value: value["observations"][5]["terminal"].update(warnings_error="RuntimeError"),
        lambda value: value["observations"][5]["terminal"].update(warnings=[["Warning", 1365]]),
    ):
        bad = json.loads(json.dumps(receipt))
        mutate(bad)
        try:
            judge(bad)
        except ReceiptError:
            continue
        raise AssertionError("S15 pure judge accepted an incomplete or unsafe receipt")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        _require(args.receipt is None, "self-check takes no receipt")
        self_check()
        print("S15 pure judge self-check passed")
        return 0
    _require(args.receipt is not None, "--receipt is required")
    print(judge(json.loads(args.receipt.read_text(encoding="utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
