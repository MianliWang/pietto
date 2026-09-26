"""Arrow-free Text authority/Unicode witnesses; installed probe owns real buffers."""

from dataclasses import replace
import importlib.util

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_arrow_result as arrow
from pietto._project import project_result_binding as binding
from pietto._project import project_result_contract as contract
from pietto._project.project_sql_emission import emit_project_sql
from pietto._project.project_result_contract_portable import export_result_contract
from pietto._project.project_result_contract_correspondence import verify_bound_export


@pytest.fixture(scope="module")
def roots(tmp_path_factory):
    root = tmp_path_factory.mktemp("text-roots")
    return {t: probe.text_fixture(root / t, t) for t in ("postgres", "mysql")}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_real_text_source_projection_and_independent_descriptors(roots, target):
    checked, artifact, neutral, producer = roots[target]
    binding.verify_producer_binding(producer, neutral, artifact)
    assert [f.field.label for f in producer.fields] == list(probe.TEXT_LABELS)
    assert [f.field.shape.canonical.name for f in producer.fields] == [
        "Text",
        "Text",
        "Int",
        "Bool",
        "Float",
    ]
    for bound in producer.fields[:2]:
        obs = bound.observation
        assert (
            obs.lower is obs.upper is None
            and obs.domain == "text"
            and obs.carrier == "str"
        )
        assert obs.text == binding.TextObservation(
            8,
            "UTF8" if target == "postgres" else "utf8mb4",
            "C" if target == "postgres" else "utf8mb4_0900_bin",
            "NO PAD",
            None if target == "postgres" else 8,
        )
    exported = export_result_contract(neutral, checked)
    verify_bound_export(exported, checked)
    assert arrow._text_widths(producer, None) == (32, 32, None, None, None)
    requests = tuple(
        arrow.TextOffsetWidthRequest(f.field, 64) if i < 2 else None
        for i, f in enumerate(producer.fields)
    )
    assert arrow._text_widths(producer, requests) == (64, 64, None, None, None)
    assert (
        export_result_contract(neutral, checked).canonical_bytes
        == exported.canonical_bytes
    )
    assert importlib.util.find_spec("pyarrow") is None
    with pytest.raises(contract.ResultError, match="ARROW_DEPENDENCY_MISSING"):
        arrow.bind_arrow(producer)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "changes",
    (
        {"max_characters": 7},
        {"max_characters": True},
        {"max_characters": 8.0},
        {"encoding": "ASCII"},
        {"collation": "other"},
        {"padding": "PAD SPACE"},
        {"storage_length": 7},
        {"storage_length": True},
    ),
)
def test_complete_text_observation_checked_before_arrow(
    roots, target, changes, monkeypatch
):
    _, artifact, neutral, producer = roots[target]
    obs = list(probe.text_observations(target))
    observed_text = obs[0].text
    assert observed_text is not None
    obs[0] = replace(obs[0], text=replace(observed_text, **changes))

    def forbidden():
        raise AssertionError("Arrow must not repair producer lies")

    monkeypatch.setattr(arrow, "_arrow", forbidden)
    with pytest.raises(contract.ResultError, match="PRODUCER_OBSERVATION"):
        arrow.bind_arrow(binding.bind_producer(neutral, artifact, tuple(obs)))
    binding.verify_producer_binding(producer, neutral, artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "value",
    (
        b"a",
        bytearray(b"a"),
        memoryview(b"a"),
        1,
        True,
        1.0,
        probe.TextSubclass("a"),
        probe.CoercibleText(),
        "abcdef中😀x",
    ),
)
def test_text_requires_exact_str_and_codepoint_domain(roots, target, value):
    with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
        arrow._value(value, roots[target][3].fields[0])


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_unicode_exact_sequence_and_strict_bounded_utf8(roots, target):
    bound = roots[target][3].fields[0]
    for value, expected_hex, characters in zip(
        probe.TEXT_VALUES, probe.TEXT_HEX, probe.TEXT_LENGTHS, strict=True
    ):
        assert arrow._value(value, bound) is value
        assert len(value) == characters
        assert value.encode("utf-8").hex() == expected_hex
        assert (
            arrow._text_bytes(value, len(expected_hex) // 2) == len(expected_hex) // 2
        )
        if value:
            with pytest.raises(contract.ResultError, match="LIMIT"):
                arrow._text_bytes(value, len(expected_hex) // 2 - 1)
    for bad in ("\ud800", "\udfff", "a\ud800z"):
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._text_bytes(bad, 64)
    assert arrow._value("", bound) == ""
    with pytest.raises(contract.ResultError, match="NULL"):
        arrow._value(None, bound)
    assert arrow._value(None, roots[target][3].fields[1]) is None
    if target == "postgres":
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._value("a\0b", bound)
    else:
        assert arrow._value("a\0b", bound) == "a\0b"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_zero_and_one_character_domain_are_not_byte_or_grapheme_counts(
    tmp_path, target
):
    for maximum in (0, 1):
        _, _, _, producer = probe.text_fixture(
            tmp_path / str(maximum), target, mixed=False, maximum=maximum
        )
        bound = producer.fields[0]
        assert arrow._value("", bound) == ""
        for value in ("é", "中", "😀"):
            if maximum:
                assert arrow._value(value, bound) == value
            else:
                with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
                    arrow._value(value, bound)
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._value("e\u0301", bound)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_positional_requests_precede_dependency_and_cannot_impersonate_int(
    roots, target, monkeypatch
):
    producer = roots[target][3]
    f0, f1 = (f.field for f in producer.fields[:2])
    r0, r1 = arrow.TextOffsetWidthRequest(f0, 64), arrow.TextOffsetWidthRequest(f1, 64)

    def forbidden():
        raise AssertionError("invalid adaptation reached Arrow")

    monkeypatch.setattr(arrow, "_arrow", forbidden)
    for requests in (
        (),
        [],
        (r0,),
        (r0, r1, None, None, None, None),
        (r0, r0, None, None, None),
        (r1, r0, None, None, None),
        (arrow.TextOffsetWidthRequest(replace(f0), 64), r1, None, None, None),
        (
            r0,
            r1,
            arrow.TextOffsetWidthRequest(producer.fields[2].field, 64),
            None,
            None,
        ),
        (arrow.TextOffsetWidthRequest(f0, True), r1, None, None, None),
        (arrow.TextOffsetWidthRequest(f0, 128), r1, None, None, None),
        (arrow.IntegerWidthRequest(f0, 32), r1, None, None, None),
    ):
        with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
            arrow.bind_arrow(producer, text_offset_widths=requests)
    with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
        arrow.bind_arrow(
            producer,
            integer_widths=(arrow.IntegerWidthRequest(f0, 32), None, None, None, None),
        )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_supported_same_neutral_root_and_blocked_upstream_descriptors(roots, target):
    import json

    checked, _, neutral, producer = roots[target]
    alternate = emit_project_sql(checked, probe.text_input(target, maximum=7, length=9))
    assert alternate.status == "VERIFIED"
    alternate_bound = binding.bind_producer(
        neutral,
        alternate.artifact,
        probe.text_observations(target, maximum=7, length=9),
    )
    assert alternate_bound.contract is producer.contract
    for key, value in (
        ("encoding", "other"),
        ("collation", "other"),
        ("padding", "PAD SPACE"),
    ):
        doc = json.loads(probe.text_input(target))
        doc["sources"][0]["fields"][0]["representation"]["domain"][key] = value
        result = emit_project_sql(checked, json.dumps(doc).encode())
        assert result.status == "BLOCKED" and result.artifact is None


def test_resource_arithmetic_preserves_numeric_allowance(roots):
    producer = roots["postgres"][3]
    for bits, expected in ((32, 45), (64, 61)):
        requests = tuple(
            arrow.TextOffsetWidthRequest(f.field, bits) if i < 2 else None
            for i, f in enumerate(producer.fields)
        )
        bound = arrow.ArrowResultBinding(producer, None, text_offset_widths=requests)
        assert (
            arrow._base_charge(bound, 1, arrow.BatchLimits(bytes=expected)) == expected
        )
        with pytest.raises(contract.ResultError, match="LIMIT"):
            arrow._base_charge(bound, 1, arrow.BatchLimits(bytes=expected - 1))
        assert arrow._base_charge(bound, 0, arrow.BatchLimits()) == bits // 4


def test_external_text_oracle_discriminates_valid_substitutions():
    for bits in (32, 64):
        for column, row, value in (
            (0, 6, "é"),
            (0, 8, "x"),
            (0, 2, "a"),
            (1, 0, ""),
            (0, 1, "b"),
        ):
            expected = probe.text_expected(bits)
            probe.text_value_oracle(expected, bits)
            expected["columns"][column][row] = value
            with pytest.raises(ValueError, match="correspondence"):
                probe.text_value_oracle(expected, bits)
