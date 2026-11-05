from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from _pietto_parser_layout import layout_free
from pietto import cli, source_format
from pietto.indentation import IndentationResult, find_leading_tab_diagnostics
from pietto.parser_api import parse_source
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


def _parseable(name: str) -> str:
    """A corpus file's text; the acceptance corpus is its parseable files."""

    try:
        source = (REPO_ROOT / name).read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        pytest.skip("the file is not UTF-8")
    if format_source(source).source is None:
        pytest.skip("the file has parser errors")
    return source


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


@pytest.mark.parametrize("name", CORPUS)
def test_corpus_formatting_is_idempotent_and_keeps_comments_and_ast(
    name: str,
) -> None:
    source = _parseable(name)
    formatted = _formatted(source)
    assert _formatted(formatted) == formatted
    # Indentation, trailing blanks and blank runs added to either give one result.
    assert _formatted(_messy(source)) == _formatted(_messy(formatted))
    assert _comments(formatted) == _comments(source)
    assert _non_blank(formatted) == _non_blank(source)
    before, after = parse_source(source), parse_source(formatted)
    assert layout_free(after.ast) == layout_free(before.ast)
    assert [item.code for item in after.diagnostics] == [
        item.code for item in before.diagnostics
    ]


@pytest.mark.parametrize("name", CORPUS)
def test_corpus_checks_and_emits_the_same_after_formatting(
    name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _parseable(name)
    copy = tmp_path / Path(name).name
    copy.write_bytes(source.encode("utf-8"))
    expected = _observed(copy, capsys)
    for formatted in (_formatted(source), _formatted(_messy(source))):
        copy.write_bytes(formatted.encode("utf-8"))
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
            "pietto 1\nmode loose\nquery q:\n  from a\n  where x -- 1 > 0\n"
            "  select x\n",
            "pietto 1\nmode loose\n\nquery q:\n    from a\n    where x -- 1 > 0\n"
            "    select x\n",
            id="header_and_minus_signs",
        ),
        pytest.param(
            "\n\npietto 1\t\nmode   loose   # m \r\nquery q:\n  from a\n  select x\n",
            "pietto 1\t\nmode   loose   # m \n\nquery q:\n    from a\n    select x\n",
            id="header_lines_are_kept_as_written",
        ),
        pytest.param(
            'pietto 1\nmode loose\nsource a = postgres.table("a")\n',
            'pietto 1\nmode loose\n\nsource a = postgres.table("a")\n',
            id="one_line_declaration_after_the_header",
        ),
        pytest.param(
            'pietto 1\n# c\nsource a = postgres.table("a")\n',
            'pietto 1\n\n# c\nsource a = postgres.table("a")\n',
            id="blank_line_after_the_header_goes_above_the_comment",
        ),
        pytest.param(
            "pietto 1\n# c\n\nquery q:\n  from a\n  select x\n",
            "pietto 1\n\n# c\nquery q:\n    from a\n    select x\n",
            id="comment_after_the_header_joins_the_declaration",
        ),
        pytest.param(
            '# c\n\npietto 1\nmode loose\nsource a = postgres.table("a")\n',
            '# c\npietto 1\nmode loose\n\nsource a = postgres.table("a")\n',
            id="comment_over_the_header_joins_it",
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
            'pietto 1\nfrom "m.pietto" import shape A\n',
            'pietto 1\n\nfrom "m.pietto" import shape A\n',
            id="the_header_is_not_an_import",
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
        pytest.param(
            "pietto 1\n\n\n# a\n\n# b\n",
            "pietto 1\n\n# a\n\n# b\n",
            id="comment_lines_under_a_header_with_nothing_below",
        ),
        pytest.param(
            "pietto 1\n# a\n",
            "pietto 1\n# a\n",
            id="comment_line_directly_under_a_header_with_nothing_below",
        ),
        pytest.param("", "", id="empty"),
        pytest.param("  # only\n\n", "# only\n", id="comment_only"),
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
