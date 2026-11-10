#!/usr/bin/env python3
"""No-DB S09 candidate preparation check.

This checks deterministic public-value-to-private-argument preparation only.
It neither imports Pietto nor opens a driver, so it cannot establish MySQL SQL
or metadata behavior.
"""

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from uuid import UUID

I64 = 1 << 63


def decimal_fits(value: Decimal, precision: int, scale: int) -> bool:
    if not value.is_finite() or not 1 <= precision <= 65 or not 0 <= scale <= min(precision, 30):
        return False
    with localcontext() as context:
        context.prec = 66
        try:
            exact = value.quantize(Decimal(1).scaleb(-scale))
        except InvalidOperation:
            return False
    return exact == value and len(exact.as_tuple().digits) <= precision


def public_text(tag: str, value: object) -> str:
    if tag == "Decimal" and type(value) is Decimal and value.is_finite():
        with localcontext() as context:
            context.prec = 66
            normalized = value.normalize()
        return "0" if normalized == 0 else format(normalized, "f")
    if tag == "Date" and type(value) is date:
        return value.isoformat()
    if tag == "Timestamp" and type(value) is datetime and value.tzinfo is None:
        if datetime(1000, 1, 1) <= value <= datetime(9999, 12, 31, 23, 59, 59, 499999):
            return value.isoformat(sep=" ", timespec="microseconds")
    if tag == "UUID" and type(value) is UUID:
        return str(value)
    raise ValueError("invalid public typed value")


def mysql_anchor(tag: str, decimal: tuple[int, int] | None = None) -> str:
    if tag == "Decimal" and decimal is not None:
        precision, scale = decimal
        if 1 <= precision <= 65 and 0 <= scale <= min(precision, 30):
            return f"CAST(? AS DECIMAL({precision},{scale}))"
    if tag == "Date":
        return "CAST(? AS DATE)"
    if tag == "Timestamp":
        return "CAST(? AS DATETIME(6))"
    if tag == "UUID":
        return "CAST(? AS BINARY(16))"
    raise ValueError("unsupported anchor")


def mysql_native_argument(tag: str, value: object) -> object:
    if value is None:
        return None
    if tag == "UUID":
        if type(value) is not UUID:
            raise ValueError("invalid UUID")
        return value.bytes
    return public_text(tag, value)


def main() -> None:
    decimal = Decimal("99999999999999999999999999999999999.999999999999999999999999999999")
    assert decimal_fits(decimal, 65, 30)
    assert not decimal_fits(Decimal("1.001"), 3, 2)
    assert not decimal_fits(Decimal("Infinity"), 3, 2)
    assert mysql_anchor("Decimal", (65, 30)) == "CAST(? AS DECIMAL(65,30))"
    assert mysql_anchor("Date") == "CAST(? AS DATE)"
    assert mysql_anchor("Timestamp") == "CAST(? AS DATETIME(6))"
    assert public_text("Date", date(1000, 1, 1)) == "1000-01-01"
    assert public_text("Date", date(9999, 12, 31)) == "9999-12-31"

    stamp = datetime(2026, 11, 8, 1, 2, 3, 4)
    assert public_text("Timestamp", stamp) == "2026-11-08 01:02:03.000004"
    try:
        public_text("Timestamp", stamp.replace(tzinfo=timezone.utc))
    except ValueError:
        pass
    else:
        raise AssertionError("aware Timestamp accepted")

    value = UUID("00112233-4455-6677-8899-aabbccddeeff")
    high = UUID("f1223344-5566-7788-99aa-bbccddeeff00")
    assert mysql_anchor("UUID") == "CAST(? AS BINARY(16))"
    assert public_text("UUID", value) == "00112233-4455-6677-8899-aabbccddeeff"
    assert mysql_native_argument("UUID", value) == bytes.fromhex("00112233445566778899aabbccddeeff")
    assert mysql_native_argument("UUID", high) == bytes.fromhex("f12233445566778899aabbccddeeff00")
    assert mysql_native_argument("UUID", value) != value.bytes_le
    assert mysql_native_argument("UUID", None) is None

    # MySQL receives every authored occurrence, while public UUID wire is text.
    occurrences = (value, high, None, value)
    assert tuple(mysql_native_argument("UUID", item) for item in occurrences) == (
        value.bytes,
        high.bytes,
        None,
        value.bytes,
    )
    assert [public_text("UUID", item) for item in occurrences if item is not None] == [
        str(value),
        str(high),
        str(value),
    ]

    hostile = "' OR 1=1 -- ?"
    assert hostile not in mysql_anchor("UUID")
    try:
        mysql_native_argument("UUID", hostile)
    except ValueError:
        pass
    else:
        raise AssertionError("non-UUID injection payload accepted")
    print("pure parameter preparation self-check: PASS")


if __name__ == "__main__":
    main()

