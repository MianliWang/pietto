from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    QueryDef,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source


def test_definition_union_matches_top_level_grammar() -> None:
    assert get_args(Definition) == (
        TypeDef,
        EnumDef,
        ConstraintDef,
        DeriveDef,
        ShapeDef,
        SourceDef,
        TableDef,
        QueryDef,
    )


@pytest.mark.parametrize(
    "body",
    [
        "    select:\n        id\n",
        "    from input_relation\n",
        "    from input_relation\n    select:\n",
        "    from input_relation\n    select:\n        alias =\n",
    ],
)
def test_table_and_query_malformed_body_diagnostics_are_consistent(
    body: str,
) -> None:
    path = Path("examples/relations/malformed.pietto")
    table_result = parse_source(f"table broken:\n{body}", path=path)
    query_result = parse_source(f"query broken:\n{body}", path=path)

    assert table_result.ast is None
    assert query_result.ast is None
    assert table_result.diagnostics == query_result.diagnostics
    assert table_result.diagnostics
    assert all(
        diagnostic.code == "PIE-P1000"
        and diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == str(path)
        for diagnostic in table_result.diagnostics
    )


@pytest.mark.parametrize("kind", ["table", "query"])
@pytest.mark.parametrize(
    "clause",
    [
        "    join accounts on row.account_id == accounts.id\n",
        "    group by account_id\n",
        "    having count(id) > 1\n",
        "    order by id\n",
        "    window recent\n",
        "    expect:\n        id is not null\n",
        "    union other_relation\n",
    ],
)
def test_relations_reject_not_yet_supported_clauses(
    kind: str,
    clause: str,
) -> None:
    result = parse_source(
        f"{kind} projected:\n    from input_relation\n{clause}    select:\n        id\n"
    )

    assert result.ast is None
    assert any(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)
