"""Cross-module `relationship` imports and exports in EXPLICIT_MODULES projects.

A relationship is bound by the same exports and imports as every other
declaration, before any call is bound; its body and parameter shapes are
checked once, in the module that declares it, and a call in an importer binds
its rows as a call of a local relationship does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pietto.cli as cli

SHAPES = (
    "shape Order:\n"
    "    id: Int\n"
    "    customer_id: Int\n"
    "shape Customer:\n"
    "    id: Int\n"
    "    status: Text | None\n"
)
SOURCES = (
    'source orders: Order = postgres.table("shop.orders")\n'
    'source customers: Customer = postgres.table("shop.customers")\n'
)
BODY = "    order.customer_id == customer.id\n"
DECLARED = "relationship OrderCustomer(order: Order, customer: Customer):\n" + BODY
EXPORTS = (
    "export shape Order, shape Customer, source orders, source customers, "
    "relationship OrderCustomer\n"
)
MODELS = EXPORTS + SHAPES + SOURCES + DECLARED
PRIVATE = MODELS.replace(", relationship OrderCustomer\n", "\n")
SOURCES_IMPORT = 'from "a.pietto" import source orders, source customers\n'
IMPORT = SOURCES_IMPORT.replace("\n", ", relationship OrderCustomer\n")


def _query(call: str = "OrderCustomer", where: str | None = None) -> str:
    """ON, a WHERE `any(...)` (or ``where``) and SELECT each call ``call``."""

    return (
        "query q:\n"
        "    from orders\n"
        "    let buyer = customers\n"
        f"    left join buyer on {call}(orders, buyer)\n"
        f"    where {where or f'any({call}(orders, c) for c in customers)'}\n"
        "    select:\n"
        "        order_id = orders.id\n"
        "        customer_id = buyer.id\n"
        f"        flag = {call}(orders, buyer)\n"
    )


def _check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str]
) -> list[tuple[str, str, int, int, str]]:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
    )
    for name, text in files.items():
        (root / name).write_text(text)
    code = cli.main(["check", "--project", str(root), "--format", "json"])
    diagnostics = json.loads(capsys.readouterr().out)["diagnostics"]
    assert code == (1 if diagnostics else 0)
    return [
        (
            item["code"],
            item["location"]["path"],
            item["location"]["line"],
            item["location"]["column"],
            item["message"],
        )
        for item in diagnostics
    ]


@pytest.mark.parametrize(
    "files",
    (
        {"b.pietto": IMPORT + _query()},
        {
            "b.pietto": 'from "a.pietto" import (\n'
            "    source orders,\n"
            "    source customers,\n"
            "    relationship OrderCustomer as oc,\n"
            ")\n" + _query("oc")
        },
        # A re-export of a re-export, renamed on the way.
        {
            "m.pietto": 'from "a.pietto" import relationship OrderCustomer as Buys\n'
            "export relationship Buys\n",
            "n.pietto": 'from "m.pietto" import relationship Buys\n'
            "export (relationship Buys)\n",
            "b.pietto": SOURCES_IMPORT
            + 'from "n.pietto" import relationship Buys\n'
            + _query("Buys"),
        },
        # The body keeps the built-in `concat` of its module; the importer's
        # own text keeps its def `concat`.
        {
            "a.pietto": MODELS.replace(
                BODY,
                '    concat(customer.status, "!") == "a!" and '
                "order.customer_id == customer.id\n",
            ),
            "b.pietto": IMPORT
            + "def concat(x: Int, y: Int) -> Int:\n    return x + y\n"
            + _query(where="concat(orders.id, 1) > 2"),
        },
        # A module's own relationship never collides with an import of
        # another kind, as before relationships were imported.
        {
            "b.pietto": SOURCES_IMPORT
            + 'from "a.pietto" import shape Order, shape Customer\n'
            + DECLARED.replace("OrderCustomer", "customers")
            + _query("customers").replace("in customers", "in buyer")
        },
        # Nor when the module exports it beside that import.
        {
            "m.pietto": 'from "a.pietto" import source customers, shape Order, '
            "shape Customer\n"
            "export relationship customers, source customers\n"
            + DECLARED.replace("OrderCustomer", "customers"),
            "b.pietto": 'from "a.pietto" import source orders\n'
            'from "m.pietto" import relationship customers as oc, source customers\n'
            + _query("oc"),
        },
    ),
)
def test_an_imported_relationship_is_called_by_the_name_its_import_binds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str]
) -> None:
    assert _check(tmp_path, capsys, {"a.pietto": MODELS, **files}) == []


COLLISION = "Import binding collides with a local declaration: OrderCustomer"
HINT = "; import relationship OrderCustomer as <name>"


@pytest.mark.parametrize(
    ("importer", "expected"),
    (
        (
            IMPORT + "def OrderCustomer(x: Int, y: Int) -> Bool:\n    return x == y\n",
            [("PIE-S2706", 1, 70, COLLISION + HINT)],
        ),
        (
            IMPORT + 'from "a.pietto" import shape Order, shape Customer\n' + DECLARED,
            [("PIE-S2706", 1, 70, COLLISION + HINT)],
        ),
        (
            IMPORT + "constraint OrderCustomer(x: Int) -> Bool:\n    return x > 0\n",
            [("PIE-S2706", 1, 70, COLLISION + HINT)],
        ),
        (
            SOURCES_IMPORT
            + 'from "c.pietto" import def OrderCustomer\n'
            + 'from "a.pietto" import relationship OrderCustomer\n',
            [
                (
                    "PIE-S2706",
                    2,
                    28,
                    "Import binding name is ambiguous: OrderCustomer; import def "
                    "OrderCustomer as <name>",
                )
            ],
        ),
        # The hint names the relationship item, also when it comes second.
        (
            SOURCES_IMPORT + 'from "a.pietto" import shape Order as OrderCustomer, '
            "relationship OrderCustomer\n",
            [
                (
                    "PIE-S2706",
                    2,
                    39,
                    "Import binding name is ambiguous: OrderCustomer" + HINT,
                )
            ],
        ),
        (
            SOURCES_IMPORT
            + 'from "a.pietto" import relationship OrderCustomer as concat, '
            "relationship OrderCustomer as round\n",
            [
                (
                    "PIE-S2398",
                    2,
                    column,
                    f"Import binding {name} has the name of a built-in function; a "
                    "relationship cannot shadow one",
                )
                for column, name in ((24, "concat"), (62, "round"))
            ],
        ),
        (
            SOURCES_IMPORT + 'from "a.pietto" import def OrderCustomer\n',
            [
                (
                    "PIE-S2705",
                    2,
                    28,
                    "Imported declaration has another kind: def OrderCustomer from "
                    '"a.pietto" is a relationship; write relationship OrderCustomer',
                )
            ],
        ),
    ),
)
def test_each_failed_relationship_import_is_reported_at_its_item_and_none_wins(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    importer: str,
    expected: list[tuple[str, int, int, str]],
) -> None:
    # A relationship import error stops the check before semantic analysis,
    # as a def import error does: the unknown field is not reported.
    other = "export def OrderCustomer\ndef OrderCustomer(x: Int) -> Bool:\n    return x > 0\n"
    files = {
        "a.pietto": MODELS,
        "c.pietto": other,
        "b.pietto": importer + _query(where="missing > 0"),
    }
    assert _check(tmp_path, capsys, files) == [
        (code, "b.pietto", line, column, message)
        for code, line, column, message in expected
    ]


@pytest.mark.parametrize(
    ("models", "expected"),
    (
        (
            PRIVATE,
            (
                "PIE-S2705",
                "b.pietto",
                1,
                70,
                "Imported declaration is private or not exported: relationship "
                'OrderCustomer from "a.pietto"',
            ),
        ),
        (
            MODELS.replace("OrderCustomer\n", "OrderCustomer, relationship Nope\n", 1),
            (
                "PIE-S2704",
                "a.pietto",
                1,
                111,
                "Unknown export binding: relationship Nope",
            ),
        ),
        (
            MODELS + DECLARED,
            (
                "PIE-S2704",
                "a.pietto",
                1,
                83,
                "Ambiguous local export declaration: relationship OrderCustomer",
            ),
        ),
    ),
)
def test_an_export_or_import_the_declaring_module_does_not_offer_is_refused(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    models: str,
    expected: tuple[str, str, int, int, str],
) -> None:
    files = {"a.pietto": models, "b.pietto": IMPORT + _query()}
    assert _check(tmp_path, capsys, files) == [expected]


def test_a_relationship_imported_along_an_import_cycle_is_blocked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The cycle is reported; no call is bound, and none adds an unknown
    # function or row argument error.
    declaring = MODELS + 'from "b.pietto" import source extra\n'
    importer = (
        IMPORT + 'export source extra\nsource extra: Order = postgres.table("x")\n'
    )
    files = {"a.pietto": declaring, "b.pietto": importer + _query()}
    assert _check(tmp_path, capsys, files) == [
        (
            "PIE-S2703",
            "b.pietto",
            1,
            6,
            "Module import cycle detected: a.pietto -> b.pietto -> a.pietto",
        )
    ]


@pytest.mark.parametrize(
    ("models", "importer", "expected"),
    (
        # The parameter shape is the declaring module's: a source of the
        # importer's own `Order` has another shape identity.
        (
            MODELS,
            IMPORT
            + "shape Order:\n    id: Int\n    customer_id: Int\n"
            + 'source own: Order = postgres.table("own")\n'
            + "query q:\n"
            + "    from own\n"
            + "    let buyer = customers\n"
            + "    left join buyer on OrderCustomer(own, buyer)\n"
            + "    select:\n"
            + "        id = own.id\n",
            [
                (
                    "PIE-S2604",
                    "b.pietto",
                    9,
                    38,
                    "Relationship OrderCustomer parameter order requires declared "
                    "shape Order; the actual row has a different shape identity",
                )
            ],
        ),
        # A body error is reported once, at the declaration; the calls are
        # told what calls of the same local relationship are told.
        (
            MODELS.replace(BODY, "    order.customer_id == customer.nope\n"),
            IMPORT + _query(where="orders.id > 0"),
            [
                (
                    "PIE-S2604",
                    "a.pietto",
                    11,
                    26,
                    "Unknown relationship parameter field: customer.nope",
                ),
                (
                    "PIE-S2604",
                    "b.pietto",
                    5,
                    24,
                    "Relationship predicate OrderCustomer has no unambiguous "
                    "checked declaration",
                ),
            ],
        ),
        (
            MODELS,
            IMPORT
            + _query(where="orders.id > 0").replace(
                "flag = OrderCustomer(orders, buyer)", "flag = OrderCustomer(orders)"
            ),
            [
                (
                    "PIE-S2604",
                    "b.pietto",
                    10,
                    16,
                    "Invalid arguments for relationship OrderCustomer: expected 2, "
                    "got 1",
                )
            ],
        ),
    ),
)
def test_call_errors_are_at_the_call_and_template_errors_at_the_declaration_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    models: str,
    importer: str,
    expected: list[tuple[str, str, int, int, str]],
) -> None:
    files = {"a.pietto": models, "b.pietto": importer}
    assert _check(tmp_path, capsys, files) == expected


def test_a_call_of_a_relationship_whose_shape_import_failed_follows_that_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The declaring module's failed shape import is the only error: neither
    # the declaration nor a call in the importer adds one.
    models = (
        'from "c.pietto" import shape Order\n'
        "export relationship OrderCustomer\n"
        "shape Customer:\n    id: Int\n    status: Text | None\n" + DECLARED
    )
    importer = (
        'from "a.pietto" import relationship OrderCustomer\n'
        + SHAPES
        + SOURCES
        + _query(where="orders.id > 0")
    )
    files = {"c.pietto": SHAPES, "a.pietto": models, "b.pietto": importer}
    assert _check(tmp_path, capsys, files) == [
        (
            "PIE-S2705",
            "a.pietto",
            1,
            30,
            'Imported declaration is private or not exported: shape Order from "c.pietto"',
        )
    ]


@pytest.mark.parametrize(
    ("models", "call", "expected"),
    (
        (
            MODELS,
            "OrderCustomer",
            "Unknown function: OrderCustomer; OrderCustomer is a relationship "
            'exported by a.pietto: import it with from "a.pietto" import '
            "relationship OrderCustomer",
        ),
        (
            PRIVATE,
            "OrderCustomer",
            "Unknown function: OrderCustomer; OrderCustomer is a relationship "
            "declared but not exported by a.pietto: export it there with export "
            'relationship OrderCustomer, then import it with from "a.pietto" import '
            "relationship OrderCustomer",
        ),
        # A qualified call is told to call the imported name.
        (
            MODELS,
            "a.OrderCustomer",
            "Unknown function: a.OrderCustomer; OrderCustomer is a relationship "
            'exported by a.pietto: import it with from "a.pietto" import '
            "relationship OrderCustomer, then call OrderCustomer(...)",
        ),
    ),
)
def test_an_unknown_function_says_how_to_import_the_relationship_of_another_module(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    models: str,
    call: str,
    expected: str,
) -> None:
    importer = SOURCES_IMPORT + _query(call, where="orders.id > 0")
    assert _check(tmp_path, capsys, {"a.pietto": models, "b.pietto": importer}) == [
        ("PIE-S2103", "b.pietto", 5, 24, expected)
    ]


POS = "export def pos\ndef pos(x: Int) -> Bool:\n    return x > 0\n"
POS_QUERY = (
    _query(where="pos(orders.id)")
    .replace("left join buyer on OrderCustomer(orders, buyer)", "cross join buyer")
    .replace("        flag = OrderCustomer(orders, buyer)\n", "")
)
CANNOT_IMPORT = (
    "Unknown function: OrderCustomer; OrderCustomer is a relationship of "
    "a.pietto, which a module cannot import: declare it in this module"
)


@pytest.mark.parametrize(
    ("files", "expected"),
    (
        # The only declaring module imports the module of the call.
        (
            {
                "a.pietto": MODELS + 'from "b.pietto" import source extra\n',
                "b.pietto": SHAPES
                + SOURCES
                + 'export source extra\nsource extra: Order = postgres.table("x")\n'
                + _query(where="orders.id > 0"),
            },
            [("PIE-S2103", "b.pietto", 14, 24, CANNOT_IMPORT)],
        ),
        # The module of the call declares the name itself.
        (
            {
                "a.pietto": MODELS,
                "b.pietto": SOURCES_IMPORT
                + "shape OrderCustomer:\n    id: Int\n"
                + _query(where="orders.id > 0"),
            },
            [("PIE-S2103", "b.pietto", 7, 24, CANNOT_IMPORT)],
        ),
        # ... or imports it.
        (
            {
                "a.pietto": MODELS,
                "b.pietto": SOURCES_IMPORT
                + 'from "c.pietto" import shape OrderCustomer\n'
                + _query(where="orders.id > 0"),
                "c.pietto": "export shape OrderCustomer\n"
                "shape OrderCustomer:\n    id: Int\n",
            },
            [("PIE-S2103", "b.pietto", 6, 24, CANNOT_IMPORT)],
        ),
        (
            {
                "a.pietto": MODELS + POS,
                "b.pietto": SOURCES_IMPORT + "shape pos:\n    id: Int\n" + POS_QUERY,
            },
            [
                (
                    "PIE-S2103",
                    "b.pietto",
                    8,
                    11,
                    "Unknown function: pos; pos is a def of a.pietto, which a "
                    "module cannot import: declare it in this module",
                )
            ],
        ),
    ),
)
def test_a_call_that_no_import_can_bind_is_told_to_declare_it_in_its_module(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    files: dict[str, str],
    expected: list[tuple[str, str, int, int, str]],
) -> None:
    assert _check(tmp_path, capsys, files) == expected
