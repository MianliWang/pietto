from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from _pietto_parser_layout import layout_free
from _pietto_sql_emission import CONFIG, fixture as emission_fixture
from pietto import cli, source_format
from pietto.indentation import IndentationResult, find_leading_tab_diagnostics
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.source_format import FormatRefusedError, format_source

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = sorted(
    path.relative_to(REPO_ROOT).as_posix()
    for folder in ("examples", "tests/fixtures")
    for path in (REPO_ROOT / folder).rglob("*.pietto")
)


def _formatted(source: str) -> str:
    result = format_source(source)
    assert result.source is not None, result.diagnostics
    return result.source


def _parseable(name: str) -> tuple[str, str]:
    """A corpus file's text and its formatted text; the acceptance corpus is
    its parseable files."""

    try:
        source = (REPO_ROOT / name).read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        pytest.skip("the file is not UTF-8")
    formatted = format_source(source).source
    if formatted is None:
        pytest.skip("the file has parser errors")
    return source, formatted


def _non_blank(source: str) -> str:
    return re.sub(r"[ \t\r\n]", "", source)


def _comments(source: str) -> list[str]:
    """The comment texts, read from the gaps between the lexer's tokens."""

    comments: list[str] = []
    cursor = 0
    for token in source_format._tokens(source)[0]:
        gap = source[cursor : token.start]
        if "#" in gap:
            comments.append(gap[gap.index("#") :].rstrip(" \t"))
        cursor = token.stop + 1
    return comments


def _messy(source: str) -> str:
    """The same tokens with doubled indentation, trailing blanks and blank runs."""

    lines = re.split(r"\r\n|\r|\n", source)
    return "\n".join(
        " " * (len(line) - len(line.lstrip(" "))) + line + "  " + ("\n\n" * (not line))
        for line in lines
    )


def _observed(
    path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, list[str], list[tuple[int, str]]]:
    """The check exit code and codes and each dialect's exit code and SQL."""

    checked = cli.main(["check", "--format", "json", str(path)])
    document = json.loads(capsys.readouterr().out)
    emitted = [
        (
            cli.main(["emit-sql", str(path), "--dialect", dialect]),
            capsys.readouterr().out,
        )
        for dialect in ("postgres", "mysql")
    ]
    return checked, [item["code"] for item in document["diagnostics"]], emitted


def _without_source_positions(output: str) -> list[Any]:
    """A project emission batch without what follows the source text: each
    module's size and digest, and the source ranges of the SQL."""

    items = json.loads(output)["items"]
    for item in items:
        del item["document"]["ranges"]
        for source in item["document"]["request"]["sources"]:
            del source["byte_count"], source["sha256"]
    return items


def test_project_fmt_lays_out_each_module_as_fmt_lays_out_one_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    item = emission_fixture("postgres", "N_imported_chain", "bag")
    (tmp_path / "pietto.toml").write_text(CONFIG, encoding="utf-8")
    (tmp_path / "contract.json").write_text(item["contract"], encoding="utf-8")
    modules = {name: _messy(text) for name, text in item["source"].items()}
    for name, text in modules.items():
        (tmp_path / name).write_bytes(text.encode("utf-8"))
    emit = ["emit-sql", "--project", str(tmp_path), "--all", "--dialect", "postgres"]
    emit += ["--emission-contract", "contract.json"]

    def observed() -> tuple[int, str, int, list[Any]]:
        checked = cli.main(["check", "--project", str(tmp_path)])
        check_output = capsys.readouterr().out
        emitted = cli.main(emit)
        return (
            checked,
            check_output,
            emitted,
            _without_source_positions(capsys.readouterr().out),
        )

    expected = observed()
    assert expected[0] == expected[2] == 0 and len(expected[3]) == 3

    assert cli.main(["fmt", "--write", "--project", str(tmp_path)]) == 0

    assert sorted(modules) == ["a.pietto", "b.pietto", "main.pietto"]
    for name, text in modules.items():
        assert (tmp_path / name).read_bytes().decode("utf-8") == _formatted(text)
    assert observed() == expected


@pytest.mark.parametrize("name", CORPUS)
def test_corpus_formatting_is_idempotent_and_keeps_comments_ast_and_output(
    name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source, formatted = _parseable(name)
    assert _formatted(formatted) == formatted
    # Indentation, trailing blanks and blank runs added to either give one result.
    messy = _formatted(_messy(source))
    assert messy == _formatted(_messy(formatted))
    assert _comments(formatted) == _comments(source)
    assert _non_blank(formatted) == _non_blank(source)
    before, after = parse_source(source), parse_source(formatted)
    assert layout_free(after.ast) == layout_free(before.ast)
    assert [item.code for item in after.diagnostics] == [
        item.code for item in before.diagnostics
    ]
    # `check` and both dialects' `emit-sql`, observed fresh before formatting.
    copy = tmp_path / Path(name).name
    copy.write_bytes(source.encode("utf-8"))
    expected = _observed(copy, capsys)
    for candidate in (formatted, messy):
        copy.write_bytes(candidate.encode("utf-8"))
        assert _observed(copy, capsys) == expected


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param(
            "shape A:\n  id: Int\n  name: Text\n",
            "shape A:\n    id: Int\n    name: Text\n",
            id="two_spaces_become_four",
        ),
        pytest.param(
            "shape A:   \n    id: Int\t \n",
            "shape A:\n    id: Int\n",
            id="trailing_whitespace",
        ),
        pytest.param(
            "shape A:\r\n  id: Int\n  name: Text\r",
            "shape A:\r\n    id: Int\r\n    name: Text\r\n",
            id="first_line_ending_crlf",
        ),
        pytest.param(
            "shape A:\r  id: Int\r\n",
            "shape A:\r    id: Int\r",
            id="first_line_ending_cr",
        ),
        pytest.param(
            "shape A:  # a\r\n  id: Int # b\r\n# c\r\n",
            "shape A:  # a\r\n    id: Int  # b\r\n# c\r\n",
            id="comments_in_a_crlf_file",
        ),
        pytest.param(
            "shape A:  # a\r  id: Int # b\r# c",
            "shape A:  # a\r    id: Int  # b\r# c\r",
            id="comments_in_a_cr_file",
        ),
        pytest.param(
            "\ufeffshape A:\n  id: Int",
            "\ufeffshape A:\n    id: Int\n",
            id="bom_kept_and_one_final_newline",
        ),
        pytest.param(
            'source a   =  postgres.table( "a # b" )   # c  #  d \n',
            'source a   =  postgres.table( "a # b" )  # c  #  d\n',
            id="spaces_between_tokens_strings_and_end_of_line_comment",
        ),
        pytest.param(
            "\n\n# head\n\n\n\nshape A:\n    id: Int\n\n\n\n    name: Text\n\n\n",
            "# head\nshape A:\n    id: Int\n\n    name: Text\n",
            id="blank_runs",
        ),
        pytest.param(
            'source a = postgres.table("a")\nsource b = postgres.table("b")\n'
            'shape A:\n    id: Int\n# about c\nsource c = postgres.table("c")\n',
            'source a = postgres.table("a")\n\nsource b = postgres.table("b")\n\n'
            'shape A:\n    id: Int\n\n# about c\nsource c = postgres.table("c")\n',
            id="declarations_are_set_apart",
        ),
        pytest.param(
            'source a = postgres.table("a")\n# about A\nshape A:\n    id: Int\n',
            'source a = postgres.table("a")\n\n# about A\nshape A:\n    id: Int\n',
            id="leading_comment_stays_with_its_declaration",
        ),
        pytest.param(
            "shape A:\n# first\n  id: Int\n      # in A\n# top\nshape B:\n  id: Int\n"
            "  # end of B\n",
            "shape A:\n    # first\n    id: Int\n    # in A\n\n# top\nshape B:\n"
            "    id: Int\n    # end of B\n",
            id="comment_lines",
        ),
        pytest.param(
            "query q:\n  from a\n  where (x >\n          1  # one\n     or y)\n"
            "  select x\n",
            "query q:\n    from a\n    where (x >\n            1  # one\n       or y)\n"
            "    select x\n",
            id="continuation_lines_move_with_their_line",
        ),
        pytest.param(
            'from "m.pietto" import (\n  shape A,  # a\n  # b\n  source s,\n)\n'
            "export (\n    shape A,# c\n  # d\n    source s)\n",
            'from "m.pietto" import (\n  shape A,  # a\n  # b\n  source s,\n)\n'
            "export (\n    shape A,  # c\n  # d\n    source s)\n",
            id="comments_in_import_and_export_lists",
        ),
        pytest.param(
            "shape A:\n    id: Int  # x",
            "shape A:\n    id: Int  # x\n",
            id="comment_at_eof",
        ),
        pytest.param("# only", "# only\n", id="comment_only_at_eof"),
        pytest.param(
            "shape A:\n  id: Int\r\n  name: Text\r",
            "shape A:\n    id: Int\n    name: Text\n",
            id="first_line_ending_lf",
        ),
        pytest.param(
            'source a = postgres.table(\n\n\n      # n\n  "a")\n',
            'source a = postgres.table(\n\n      # n\n  "a")\n',
            id="comment_and_blank_lines_inside_parentheses",
        ),
        pytest.param(
            "shape A:\n  id:\tInt\n",
            "shape A:\n    id:\tInt\n",
            id="tab_between_tokens",
        ),
        pytest.param(
            "\ufeff# c\nshape A:\n  id: Int\n",
            "\ufeff# c\nshape A:\n    id: Int\n",
            id="bom_then_comment",
        ),
        pytest.param(
            "# a\x0cb \u2028c\nshape A:\n  id: Int\n",
            "# a\x0cb \u2028c\nshape A:\n    id: Int\n",
            id="form_feed_and_line_separator_in_a_comment",
        ),
        pytest.param(
            'source a = postgres.table("a")\nsource b = postgres.table("b")\n\n\n'
            '# c\nsource c = postgres.table("c")\n# d\n\nsource d = postgres.table("d")\n',
            'source a = postgres.table("a")\n\nsource b = postgres.table("b")\n\n'
            '# c\nsource c = postgres.table("c")\n\n# d\nsource d = postgres.table("d")\n',
            id="one_blank_line_above_the_comment_lines_over_a_declaration",
        ),
        pytest.param(
            'source a = postgres.table("a")\n\n\nsource b = postgres.table("b")\n',
            'source a = postgres.table("a")\n\nsource b = postgres.table("b")\n',
            id="two_blank_lines_between_one_line_declarations_become_one",
        ),
        pytest.param(
            'source a = postgres.table("a")\n\n# part\n\n# about b\n\n'
            'source b = postgres.table("b")\n',
            'source a = postgres.table("a")\n\n# part\n# about b\n'
            'source b = postgres.table("b")\n',
            id="comment_lines_over_a_declaration_lose_their_blank_lines",
        ),
        pytest.param(
            'from "m.pietto" import shape A\nfrom "n.pietto" import shape B\n'
            'export shape A\nsource s = postgres.table("s")\n',
            'from "m.pietto" import shape A\nfrom "n.pietto" import shape B\n'
            'export shape A\n\nsource s = postgres.table("s")\n',
            id="imports_and_exports_written_together_stay_grouped",
        ),
        pytest.param(
            'from "m.pietto" import shape A\n\n\nfrom "n.pietto" import shape B\n\n\n'
            'export shape A\n\n\nsource s = postgres.table("s")\n',
            'from "m.pietto" import shape A\nfrom "n.pietto" import shape B\n'
            'export shape A\n\nsource s = postgres.table("s")\n',
            id="imports_and_exports_written_apart_are_grouped",
        ),
        pytest.param(
            'from "m.pietto" import shape A\n\n# about B\n\nfrom "n.pietto" import shape B\n'
            'source s = postgres.table("s")\nexport shape A\n\nexport source s\n',
            'from "m.pietto" import shape A\n# about B\nfrom "n.pietto" import shape B\n\n'
            'source s = postgres.table("s")\n\nexport shape A\nexport source s\n',
            id="a_declaration_between_two_import_groups",
        ),
        pytest.param(
            "shape A:\n  id: Int\n# tail\n\n\n\n# more\n",
            "shape A:\n    id: Int\n# tail\n\n# more\n",
            id="comment_lines_after_the_last_declaration_keep_their_blank_lines",
        ),
        pytest.param(
            "shape A:\n  id: Int\n\n\n# tail\n",
            "shape A:\n    id: Int\n\n# tail\n",
            id="blank_lines_above_the_comment_lines_after_the_last_declaration",
        ),
        pytest.param(
            "# a\n\n\n# b\n# c\n",
            "# a\n\n# b\n# c\n",
            id="comment_only_file_keeps_its_blank_lines",
        ),
        pytest.param("", "", id="empty"),
        pytest.param("  # only\n\n", "# only\n", id="comment_only"),
        pytest.param(
            'a: Int = 1\nb: Date = "2024-01-31"\n# c\nc: Text = "x"\n',
            'a: Int = 1\n\nb: Date = "2024-01-31"\n\n# c\nc: Text = "x"\n',
            id="top_level_constants_are_declarations",
        ),
    ],
)
def test_formatting_changes_only_the_whitespace_between_tokens(
    before: str, after: str
) -> None:
    result = format_source(before)
    assert result.source == after
    assert result.changed is (after != before)
    assert format_source(after).source == after
    parsed, reparsed = parse_source(before), parse_source(after)
    assert layout_free(reparsed.ast) == layout_free(parsed.ast)
    assert [item.code for item in reparsed.diagnostics] == [
        item.code for item in parsed.diagnostics
    ]


def test_minus_signs_written_together_still_warn_after_formatting() -> None:
    source = "query q:\n  from a\n  where 1 -- 2 > 0\n  select x = 1\n"
    result = format_source(source)
    assert result.source is not None
    assert [item.code for item in result.diagnostics] == ["PIE-P1009"]
    assert [item.code for item in parse_source(result.source).diagnostics] == [
        "PIE-P1009"
    ]


@pytest.mark.parametrize(
    ("source", "code"),
    [
        ("shape A:\n    id: Int\n  name: Text\n", "PIE-P1003"),
        ("shape A:\n\tid: Int\n", "PIE-P1004"),
        ("shape A:\n  id: Int\x0c\n", "PIE-P1000"),
        ('source a = postgres.table("a"\n', "PIE-P1008"),
        ("pietto 1\nshape A:\n  id: Int\n", "PIE-P1000"),  # a retired header line
    ],
)
def test_a_source_with_parser_errors_is_refused_with_its_diagnostics(
    source: str, code: str
) -> None:
    result = format_source(source)
    assert result.source is None
    assert result.diagnostics == parse_source(source).diagnostics
    assert code in [item.code for item in result.diagnostics]


def _checked(text: str) -> tuple[bool, object, object]:
    """What the self-check compares: a leading tab, the effective tokens, and
    each line's code and comment."""

    raw, joined, errors = source_format._tokens(text)
    return (
        bool(find_leading_tab_diagnostics(text, path=None)),
        source_format._effective_tokens(joined, errors),
        source_format._written(source_format._lines(text, raw, set())),
    )


COMMENTED = "shape A:  # a\n  id: Int\n"


@pytest.mark.parametrize(
    ("source", "output", "differs"),
    [
        pytest.param(
            'source a = postgres.table("a b")\n',
            'source a = postgres.table("ab")\n',
            (False, True, True),
            id="token_text",
        ),
        pytest.param(
            COMMENTED, "shape A:  # a\nid: Int\n", (False, True, False), id="block"
        ),
        pytest.param(
            COMMENTED,
            "shape A:  # a\n\tid: Int\n",
            (True, False, False),
            id="leading_tab",
        ),
        pytest.param(
            COMMENTED,
            "shape A:  # a\n    id:Int\n",
            (False, False, True),
            id="tokens_written_together",
        ),
        pytest.param(
            COMMENTED, "shape A:\n    id: Int\n", (False, False, True), id="comment"
        ),
        pytest.param(
            "shape A:  # a\n    # b\n  id: Int\n",
            "shape A:  # a  # b\n    id: Int\n",
            (False, False, True),
            id="comments_merged",
        ),
        pytest.param(
            "shape A:  # a # b\n  id: Int\n",
            "shape A:  # a\n    # b\n    id: Int\n",
            (False, False, True),
            id="comment_split",
        ),
        pytest.param(
            COMMENTED,
            "shape A:\n    # a\n    id: Int\n",
            (False, False, True),
            id="end_of_line_comment_moved_to_its_own_line",
        ),
        pytest.param(
            COMMENTED,
            "shape A:  # a\n    id: Int\n\x01\n",
            (False, True, True),
            id="unknown_character",
        ),
        pytest.param(
            'from "m.pietto" import (\n  shape A,\n  # b\n  source s)\n',
            'from "m.pietto" import (\n  shape A,\n  source s)\n',
            (False, False, True),
            id="comment_in_an_import_list",
        ),
    ],
)
def test_output_that_does_not_keep_the_source_is_refused(
    source: str,
    output: str,
    differs: tuple[bool, bool, bool],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(a != b for a, b in zip(_checked(source), _checked(output))) == differs
    monkeypatch.setattr(source_format, "_render", lambda lines, newline: output)
    with pytest.raises(FormatRefusedError, match="would not keep the source's"):
        format_source(source)


def test_effective_tokens_refuse_any_reported_or_unknown_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, joined, errors = source_format._tokens("shape A:\n  id: Int\n")
    assert errors == () and source_format._effective_tokens(joined, errors)
    reported = parse_source("shape A:\n\tid: Int\n").diagnostics
    assert source_format._effective_tokens(joined, reported) is None
    assert source_format._effective_tokens(*source_format._tokens("\x01\n")[1:]) is None
    unjoined = IndentationResult(joined.tokens, reported)
    assert source_format._effective_tokens(unjoined, ()) is None
    inject = source_format.inject_indentation

    def report(*args: Any, **kwargs: Any) -> IndentationResult:
        return IndentationResult(inject(*args, **kwargs).tokens, reported)

    monkeypatch.setattr(source_format, "inject_indentation", report)
    assert source_format._effective_tokens(joined, ()) is None
    with pytest.raises(FormatRefusedError, match="would not keep the source's"):
        format_source("shape A:\n  id: Int\n")


def test_the_check_compares_the_text_apart_from_blanks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A comment that the line split loses on both sides is still caught."""

    split = source_format._lines

    def lose_comments(*args: Any) -> list[Any]:
        return [replace(line, comment="") for line in split(*args)]

    monkeypatch.setattr(source_format, "_lines", lose_comments)
    assert format_source("shape A:\n    id: Int\n").source == "shape A:\n    id: Int\n"
    with pytest.raises(FormatRefusedError, match="would not keep the source's"):
        format_source("shape A:  # a\n    id: Int\n")


def test_the_check_refuses_when_neither_side_can_be_compared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(source_format, "_effective_tokens", lambda joined, errors: None)
    with pytest.raises(FormatRefusedError, match="would not keep the source's"):
        format_source("shape A:\n  id: Int\n")


def test_output_over_the_size_budget_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "shape A:\n  id: Int\n"
    monkeypatch.setattr(
        source_format.parser_api,
        "_source_exceeds_utf8_budget",
        lambda text: len(text) > len(source),
    )
    with pytest.raises(FormatRefusedError, match="would exceed the maximum supported"):
        format_source(source)


def test_the_asof_join_example_is_a_fixed_point_and_only_reindents() -> None:
    from _pietto_semantic_join_asof import CANONICAL

    assert _formatted(CANONICAL) == CANONICAL
    narrow = CANONICAL.replace("\n    ", "\n  ")
    assert narrow != CANONICAL and _formatted(narrow) == CANONICAL


def test_an_asof_join_fmt_cannot_admit_stays_refused_or_byte_identical() -> None:
    from _pietto_semantic_join_asof import CANONICAL

    line = (
        "asof left join price on orders.product_id == price.product_id and "
        "orders.ordered_at >= price.valid_from"
    )
    parenthesized = CANONICAL.replace(
        line,
        "asof left join price on (orders.product_id == price.product_id\n"
        "        and orders.ordered_at >= price.valid_from)",
    )
    result = format_source(parenthesized)
    assert result.source is None
    assert [item.code for item in result.diagnostics] == ["PIE-P1000"]
    reversed_ = CANONICAL.replace(
        "orders.ordered_at >= price.valid_from", "price.valid_from <= orders.ordered_at"
    )
    assert _formatted(reversed_) == reversed_
    parsed = parse_source(reversed_, path="asof.pietto")
    assert parsed.ast is not None
    assert [item.code for item in analyze(parsed.ast).diagnostics] == ["PIE-S2336"]


_CONDITIONAL_AGGREGATES = """shape Order:
    id: Int
    customer_id: Int | None
    amount_cents: Int
    paid: Bool
    status: Text | None

source orders: Order = postgres.table("shop.orders")

query customer_order_summary:
    from orders
    group by customer_id
    select:
        customer_id
        orders_count = count()
        paid_orders = sum(1 for o in group if o.paid)
        paid_cents = sum(o.amount_cents for o in group if o.paid)
        refunded_orders = sum(1 for o in group if o.status == "refunded")
"""


def test_the_conditional_aggregate_example_is_a_fixed_point_and_only_reindents() -> (
    None
):
    """The canonical generator call sits whole on its item's line; fmt adds,
    drops and respells no token of it."""
    assert _formatted(_CONDITIONAL_AGGREGATES) == _CONDITIONAL_AGGREGATES
    narrow = _CONDITIONAL_AGGREGATES.replace("\n    ", "\n  ")
    assert narrow != _CONDITIONAL_AGGREGATES
    assert _formatted(narrow) == _CONDITIONAL_AGGREGATES
    parsed = parse_source(_CONDITIONAL_AGGREGATES)
    assert parsed.ast is not None
    assert analyze(parsed.ast).diagnostics == ()


_ORDERED_VALUES = """shape Sale:
    id: Int
    shop_id: Int
    plant: Text
    pot_size: Text | None
    price_cents: Int
    weight_kg: Float | None
    sold_at: Timestamp
    sale_key = unique(id)

source sales: Sale = postgres.table("nursery.sales")

query shop_plants:
    from sales
    where weight_kg is not None
    group by shop_id
    select:
        shop_id
        first_plant = first(plant, order by sold_at, id)
        latest_plant = last(plant, order by sold_at, id)
        priciest_plant = first(plant, order by price_cents desc, id)
        cheapest_plant = first(plant, order by price_cents, id)
        lightest_pot = first(pot_size, order by weight_kg, id)
"""


def test_the_first_and_last_example_is_a_fixed_point_and_only_reindents() -> None:
    """A `first` or `last` call with its internal `order by` sits whole on its
    item's line; fmt adds, drops and respells no token of it."""
    assert _formatted(_ORDERED_VALUES) == _ORDERED_VALUES
    narrow = _ORDERED_VALUES.replace("\n    ", "\n  ")
    assert narrow != _ORDERED_VALUES
    assert _formatted(narrow) == _ORDERED_VALUES
    parsed = parse_source(_ORDERED_VALUES)
    assert parsed.ast is not None
    assert analyze(parsed.ast).diagnostics == ()
