from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Script
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticModel, SemanticResult, analyze


def test_analyze_accepts_script_and_defaults_to_checked() -> None:
    script = _parse("type Age = Int\n")

    result = analyze(script)

    assert result.model.mode is CheckMode.CHECKED


@pytest.mark.parametrize("mode", [CheckMode.LOOSE, CheckMode.STRICT])
def test_analyze_accepts_mode_overrides(mode: CheckMode) -> None:
    result = analyze(_parse(""), mode_override=mode)

    assert result.model.mode is mode


def test_analyze_uses_header_mode_and_override_takes_precedence() -> None:
    script = _parse("mode loose\n")

    assert analyze(script).model.mode is CheckMode.LOOSE
    assert (
        analyze(script, mode_override=CheckMode.STRICT).model.mode is CheckMode.STRICT
    )


def test_analyze_returns_model_and_empty_diagnostics() -> None:
    result = analyze(_parse("shape User:\n    id: UUID not null\n"))

    assert isinstance(result, SemanticResult)
    assert isinstance(result.model, SemanticModel)
    assert result.diagnostics == ()


def test_empty_semantic_namespaces_are_readonly() -> None:
    model = analyze(_parse("")).model

    assert model.type_symbols == {}
    assert model.callable_symbols == {}
    assert model.relation_symbols == {}
    with pytest.raises(TypeError):
        model.type_symbols["Age"] = object()  # type: ignore[index]


def test_semantic_result_and_model_are_frozen() -> None:
    result = analyze(_parse(""))

    with pytest.raises(FrozenInstanceError):
        result.model.mode = CheckMode.LOOSE  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.diagnostics = ()  # type: ignore[misc]


def test_analyze_does_not_mutate_parser_ast() -> None:
    script = _parse("type Age = Int\n")
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_semantic_public_objects_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            'source users: User is postgres.table("public.users")\n'
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
