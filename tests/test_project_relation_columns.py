"""Relation columns of a schema version 2 project (pietto.project-relation-columns.v1).

The view maps the completed project semantics' row field facts of every
table and query; these tests read its document through the private builder
and its serializer, which the CLI writes unchanged.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import pietto.cli as cli
import pietto._project_explain.relation_columns as relation_columns
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_completion import ProjectExistingEffectiveOutput
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectCompletedSetOutput,
    ProjectCompletedValuesOutput,
)
from pietto._project.project_sql_emission_cli import run_project_emit_sql
from pietto._project.project_sql_emission_contract import canonical
from pietto._project_explain.relation_columns import (
    build_project_relation_columns,
    serialize_project_relation_columns,
)

CONFIG = 'schema_version = 2\n\n[sources]\ninclude = ["*.pietto", "models/*.pietto"]\n'
BASE = """\
type Money = Int
enum Status:
    open
    closed
shape Customer:
    id: Int
    name: Text
shape Order:
    id: Int
    customer_id: Int
    total: Money
    note: Text | None
    status: Status
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
source archived: Order = postgres.table("archived")

export (
    shape Customer,
    shape Order,
    source customers,
    source orders,
    source archived,
)
"""
QUERIES = """\
from "models/base.pietto" import (
    source customers,
    source orders,
    source archived,
)

query flat:
    from orders
    where total > 1
    select:
        id
        note
        t = total + 1

query customers_with_orders:
    let recent:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select:
            id
            note
        order by id
    from customers
    select:
        customer_id = id
        recent_orders = collect recent

query expanded:
    from customers_with_orders
    let o = unnest(customers_with_orders.recent_orders)
    cross join o
    select:
        customer_id
        oid = o.id

table joined:
    from customers
    let o = orders
    left join o on o.customer_id == customers.id
    select:
        cid = customers.id
        oid = o.id
        note = o.note
        total = o.id + 1
        st = o.status
        money = o.total

query both:
    union all orders, archived

query seed:
    values(id: Int, label: Text | None):
        1, "new"
        2, None

query days:
    from generate_series(1, 31, 1) as n
    select:
        n
"""
FLAT = """\
enum Status:
    open
    closed
shape Order:
    id: Int
    total: Int
    note: Text | None
    status: Status
source orders: Order = postgres.table("orders")

query flat:
    from orders
    where total > 1
    select:
        id
        note
        t = total + 1
        nt = note
        status

table recent:
    from orders
    select:
        id
        status
"""


def _project(tmp_path: Path, files: dict[str, str], name: str = "project") -> Path:
    root = tmp_path / name
    for path, text in {"pietto.toml": CONFIG, **files}.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    return root


def _shop(tmp_path: Path) -> Path:
    return _project(
        tmp_path, {"models/base.pietto": BASE, "models/queries.pietto": QUERIES}
    )


def _document(root: Path) -> tuple[int, dict[str, Any]]:
    result = build_project_relation_columns(root)
    data = serialize_project_relation_columns(result)
    document = json.loads(data)
    assert data == canonical(document) + b"\n"
    assert document["format"] == "pietto.project-relation-columns.v1"
    assert document["ok"] is (result.exit_code == 0)
    assert (document["relations"] is None) is (result.exit_code != 0)
    return result.exit_code, document


def _column(column: dict[str, Any]) -> tuple[Any, ...]:
    kind, name = column["type"]["kind"], column["type"]["name"]
    if kind == "collection":
        assert set(column["type"]) == {"kind", "name", "element"} and name is None
        return (
            column["name"],
            kind,
            column["nullability"],
            tuple(_column(item) for item in column["type"]["element"]),
        )
    if kind in {"enum", "shape"}:
        # The module that declares the type, past imports and alias chains.
        assert set(column["type"]) == {"kind", "module", "name"}
        return (
            column["name"],
            name,
            kind,
            column["nullability"],
            column["type"]["module"],
        )
    assert set(column["type"]) == {"kind", "name"}
    return (column["name"], name, kind, column["nullability"])


def _relations(document: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (
            relation["module"],
            relation["kind"],
            relation["name"],
            tuple(_column(column) for column in relation["columns"]),
        )
        for relation in document["relations"]
    ]


def test_every_table_and_query_lists_its_columns_as_computed(tmp_path: Path) -> None:
    root = _shop(tmp_path)

    exit_code, document = _document(root)

    queries = "models/queries.pietto"
    assert exit_code == 0
    assert document["cli_errors"] == [] and document["diagnostics"] == []
    assert _relations(document) == [
        (
            queries,
            "query",
            "flat",
            (
                ("id", "Int", "builtin", "non_null"),
                ("note", "Text", "builtin", "nullable"),
                ("t", "Int", "builtin", "unknown"),
            ),
        ),
        (
            queries,
            "query",
            "customers_with_orders",
            (
                ("customer_id", "Int", "builtin", "non_null"),
                (
                    "recent_orders",
                    "collection",
                    "non_null",
                    (
                        ("id", "Int", "builtin", "non_null"),
                        ("note", "Text", "builtin", "nullable"),
                    ),
                ),
            ),
        ),
        (
            queries,
            "query",
            "expanded",
            (
                ("customer_id", "Int", "builtin", "non_null"),
                ("oid", "Int", "builtin", "non_null"),
            ),
        ),
        (
            queries,
            "table",
            "joined",
            (
                ("cid", "Int", "builtin", "non_null"),
                ("oid", "Int", "builtin", "nullable"),
                ("note", "Text", "builtin", "nullable"),
                ("total", "Int", "builtin", "unknown"),
                ("st", "Status", "enum", "nullable", "models/base.pietto"),
                ("money", "Int", "builtin", "nullable"),
            ),
        ),
        (
            queries,
            "query",
            "both",
            (
                ("id", "Int", "builtin", "non_null"),
                ("customer_id", "Int", "builtin", "non_null"),
                ("total", "Int", "builtin", "non_null"),
                ("note", "Text", "builtin", "nullable"),
                ("status", "Status", "enum", "non_null", "models/base.pietto"),
            ),
        ),
        (
            queries,
            "query",
            "seed",
            (
                ("id", "Int", "builtin", "non_null"),
                ("label", "Text", "builtin", "nullable"),
            ),
        ),
        (queries, "query", "days", (("n", "Int", "builtin", "non_null"),)),
    ]
    # The corpus reaches every completed entry kind a table or query has.
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    )
    overlay = completed.effective_outputs
    assert overlay is not None
    assert {
        type(entry)
        for owner, entry in zip(overlay.owners, overlay.entries, strict=True)
        if not owner.block_local
        and owner.identity.declaration_kind.value in {"table", "query"}
    } == {
        ProjectExistingEffectiveOutput,
        ProjectCompletedEffectiveOutput,
        ProjectCompletedSetOutput,
        ProjectCompletedValuesOutput,
    }


def test_relations_follow_the_emit_sql_batch_item_sequence(tmp_path: Path) -> None:
    root = _shop(tmp_path)
    # Every item is kept in the batch, refused or not, so a contract that
    # describes nothing still lists the owners.
    (root / "contract.json").write_text("{}\n", encoding="utf-8")

    batch = run_project_emit_sql(
        [
            "--project",
            str(root),
            "--all",
            "--dialect",
            "postgres",
            "--emission-contract",
            "contract.json",
            "--format",
            "json",
        ]
    )
    _exit_code, document = _document(root)

    owners = [item["owner"] for item in json.loads(batch.stdout)["items"]]
    assert len(owners) == 7
    assert [
        {key: relation[key] for key in ("module", "kind", "name")}
        for relation in document["relations"]
    ] == owners


TYPES = """\
enum Tier:
    gold
    silver
shape Addr:
    city: Text
type Phase = Tier
export (
    enum Tier,
    shape Addr,
    type Phase,
)
"""
# Re-exports what it imports and extends the alias chain.
MID = """\
from "models/types.pietto" import (
    enum Tier,
    shape Addr,
    type Phase,
)
type Stage = Phase
export (
    enum Tier,
    shape Addr,
    type Stage,
)
"""
ACCOUNTS = """\
from "models/mid.pietto" import (
    enum Tier as Level,
    shape Addr,
    type Stage,
)

enum Tier:
    x
    y
type StageN = Stage
shape Acct:
    id: Int
    level: Level
    stage: StageN
    own: Tier
    addr: Addr
source accts: Acct = postgres.table("accts")

query imported:
    from accts
    select:
        level
        stage
        addr

query local:
    from accts
    select:
        own
"""


def test_an_enum_or_shape_type_names_the_module_that_declares_it(
    tmp_path: Path,
) -> None:
    root = _project(
        tmp_path,
        {
            "models/types.pietto": TYPES,
            "models/mid.pietto": MID,
            "models/accounts.pietto": ACCOUNTS,
        },
    )

    exit_code, document = _document(root)

    types, accounts = "models/types.pietto", "models/accounts.pietto"
    assert exit_code == 0 and document["diagnostics"] == []
    # An import alias, a re-export and an alias chain all lead to the
    # declaration; the local Tier is another type of the same name.
    assert _relations(document) == [
        (
            accounts,
            "query",
            "imported",
            (
                ("level", "Tier", "enum", "non_null", types),
                ("stage", "Tier", "enum", "non_null", types),
                ("addr", "Addr", "shape", "non_null", types),
            ),
        ),
        (accounts, "query", "local", (("own", "Tier", "enum", "non_null", accounts),)),
    ]


def test_two_enums_of_one_name_differ_by_their_modules(tmp_path: Path) -> None:
    base = FLAT.replace("query flat:", "export (\n    source orders,\n)\n\nquery flat:")
    other = """\
from "main.pietto" import (
    source orders,
)

enum Status:
    open
    closed
shape Item:
    id: Int
    status: Status
source items: Item = postgres.table("items")

query mine:
    from orders
    select:
        id
        status

query theirs:
    from items
    select:
        id
        status
"""
    root = _project(tmp_path, {"main.pietto": base, "other.pietto": other})

    exit_code, document = _document(root)

    assert exit_code == 0
    assert [
        (relation["name"], relation["columns"][1]["type"])
        for relation in document["relations"]
        if relation["module"] == "other.pietto"
    ] == [
        ("mine", {"kind": "enum", "module": "main.pietto", "name": "Status"}),
        ("theirs", {"kind": "enum", "module": "other.pietto", "name": "Status"}),
    ]
    # The check, too, holds them as two types.
    (root / "other.pietto").write_text(
        other + "\nquery both:\n    union all mine, theirs\n", encoding="utf-8"
    )
    exit_code, document = _document(root)
    assert exit_code == 1
    assert [item["code"] for item in document["diagnostics"]] == ["PIE-S2343"]


@pytest.mark.parametrize(
    "case", ("no_symbol", "other_module", "other_kind", "other_name")
)
def test_an_enum_whose_declaring_module_is_not_proven_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    root = _project(tmp_path, {"main.pietto": FLAT})
    column = relation_columns._column
    refused: list[str] = []

    def unproven(field: Any, *args: Any, **kwargs: Any) -> Any:
        resolved = field.resolved_type
        if resolved.symbol is not None:
            symbol = {
                "no_symbol": None,
                "other_module": replace(resolved.symbol, path="other.pietto"),
                "other_kind": replace(resolved.symbol, kind=ProjectSymbolKind.SHAPE),
                "other_name": replace(resolved.symbol, name="Other"),
            }[case]
            field = replace(field, resolved_type=replace(resolved, symbol=symbol))
            with pytest.raises(relation_columns._Unavailable):
                column(field, *args, **kwargs)
            refused.append(field.name)
        return column(field, *args, **kwargs)

    monkeypatch.setattr(relation_columns, "_column", unproven)
    exit_code, document = _document(root)

    # The first enum column refuses the document; it names no other column.
    assert refused == ["status"]
    assert exit_code == 2 and document["diagnostics"] == []
    assert document["cli_errors"] == [
        {
            "kind": "project_resource",
            "message": "Project relation columns are unavailable.",
            "path": None,
        }
    ]


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.mark.parametrize(
    ("case", "exit_code", "codes", "errors"),
    (
        ("parse", 1, ["PIE-P1000"], []),
        ("semantic", 1, ["PIE-S2102"], []),
        ("source_read", 2, [], ["source_read"]),
        ("unnamed", 2, [], ["project_path"]),
        ("untyped_none", 2, ["PIE-S2385"], ["project_resource"]),
    ),
)
def test_a_failure_publishes_no_relations(
    tmp_path: Path,
    case: str,
    exit_code: int,
    codes: list[str],
    errors: list[str],
) -> None:
    root = _project(tmp_path, {"main.pietto": FLAT})
    if case == "parse":
        (root / "main.pietto").write_text(FLAT + "query broken:\n    from\n")
    elif case == "semantic":
        (root / "main.pietto").write_text(
            FLAT.replace("        nt = note", "        nt = nope")
        )
    elif case == "source_read":
        _write_bytes(root / "bad.pietto", b"shape Bad:\n    id: Int\n\xff\n")
    elif case == "unnamed":
        try:
            os.rename(
                os.fsencode(root / "main.pietto"), os.fsencode(root) + b"/m\xff.pietto"
            )
        except (OSError, UnicodeError):
            pytest.skip("this file system refuses a file name that is not UTF-8")
    else:
        (root / "main.pietto").write_text(FLAT + "        nothing = None\n")

    result = build_project_relation_columns(root)
    actual, document = _document(root)

    assert actual == result.exit_code == exit_code
    assert document["relations"] is None
    assert [item["code"] for item in document["diagnostics"]] == codes
    assert [item["kind"] for item in document["cli_errors"]] == errors
    if case == "unnamed":
        assert document["cli_errors"] == [
            {
                "kind": "project_path",
                "message": "Project source path must be valid UTF-8 to list relation"
                ' columns: "m\\udcff.pietto"; rename it.',
                "path": None,
            }
        ]
    if case == "untyped_none":
        # The type of an untyped None is the internal unknown name, which no
        # document shows: the view fails closed beside the warning that names it.
        assert document["cli_errors"] == [
            {
                "kind": "project_resource",
                "message": "Project relation columns are unavailable.",
                "path": None,
            }
        ]
        assert b"<unknown>" not in serialize_project_relation_columns(result)


@pytest.mark.parametrize("failure", (RecursionError, ValueError, TypeError))
def test_a_completion_that_raises_is_reported_without_relations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    root = _project(tmp_path, {"main.pietto": FLAT})

    def raising(_semantic: object) -> object:
        raise failure

    monkeypatch.setattr(
        relation_columns, "build_project_completed_semantic_result", raising
    )
    exit_code, document = _document(root)

    if failure is RecursionError:
        assert exit_code == 1 and document["cli_errors"] == []
        assert [item["code"] for item in document["diagnostics"]] == ["PIE-S2006"]
    else:
        assert exit_code == 2
        assert document["diagnostics"] == []
        assert document["cli_errors"] == [
            {
                "kind": "project_resource",
                "message": "Project relation columns are unavailable.",
                "path": None,
            }
        ]


def test_columns_agree_with_single_file_explain_on_flat_relations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # FLAT has no alias: the two disagree there (the spec's Type object
    # records it), and the money column of the first test shows this side.
    root = _project(tmp_path, {"main.pietto": FLAT})

    _exit_code, document = _document(root)
    assert cli.main(["explain", str(root / "main.pietto"), "--format", "json"]) == 0
    metadata = json.loads(capsys.readouterr().out)["metadata"]

    assert [
        (
            relation["name"],
            [
                (
                    field["name"],
                    field["type"]["name"],
                    field["type"]["kind"],
                    field["nullability"],
                )
                for field in relation["output_schema"]["fields"]
            ],
        )
        for relation in metadata["relations"]
    ] == [
        (
            relation["name"],
            [
                (
                    column["name"],
                    column["type"]["name"],
                    column["type"]["kind"],
                    column["nullability"],
                )
                for column in relation["columns"]
            ],
        )
        for relation in document["relations"]
    ]
    assert len(document["relations"]) == 2
