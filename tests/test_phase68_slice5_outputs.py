"""General correspondence: fresh original identities, unchanged old branch."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from _pietto_phase68_slice5_cases import CASES, build
from pietto._project.project_result_output import prepare_output, verify_output
from pietto._project.project_result_binding import bind_producer
from pietto._project.project_result_contract import ResultError
from pietto._project.project_execution_reader import bind_postgres_output
from pietto._project import project_arrow_result as scalar


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", CASES)
def test_current_admitted_output_domain(tmp_path, target, case, variant):
    outcome = build(tmp_path, target, case, variant)
    if outcome.status == "BLOCKED":
        assert target == "mysql" and (case, variant) in (
            ("V_join_full", "null_keys"),
            ("A_window_groups", "exclude"),
        )
        return
    assert outcome.artifact is not None
    output = prepare_output(outcome.artifact)
    assert verify_output(output, outcome.artifact, output.contract) is output.columns
    assert len(output.columns) == len(outcome.artifact.request.plan.exports)
    assert all(
        c.export is f.port
        for c, f in zip(output.columns, output.contract.shape.fields, strict=True)
    )


def test_computed_metadata_and_original_damage(tmp_path):
    outcome = build(tmp_path, "postgres", "T_row_direct", "query_bind")
    artifact = outcome.artifact
    output = prepare_output(artifact)
    metadata = tuple(
        SimpleNamespace(
            name=c.label,
            type_code=20 if c.realization.tag == "Int" else 16,
            null_ok=None,
        )
        for c in output.columns
    )
    binding = bind_postgres_output(output, metadata)
    assert binding.fields[
        1
    ].nullable  # original UNKNOWN is retained, never non-null proof
    assert binding.fields[1].field.nullability.value == "unknown"
    assert scalar._value(9007199254740994, binding.fields[1]) == 9007199254740994
    with pytest.raises(ResultError, match="^VALUE_DOMAIN$"):
        scalar._value(True, binding.fields[1])
    with pytest.raises(ResultError, match="^PRODUCER_UNSUPPORTED$"):
        bind_producer(
            output.contract, artifact, tuple(f.observation for f in binding.fields)
        )
    for columns, code in (
        (output.columns[::-1], "COLUMNS"),
        (output.columns[:-1], "INVENTORY"),
        ((*output.columns, output.columns[0]), "INVENTORY"),
        ((output.columns[0], *output.columns[:-1]), "COLUMNS"),
        (
            (replace(output.columns[0], source_field=None), *output.columns[1:]),
            "REALIZATION",
        ),
        (
            (
                output.columns[0],
                replace(output.columns[1], source_field=output.columns[0].source_field),
                *output.columns[2:],
            ),
            "REALIZATION",
        ),
        (
            (replace(output.columns[0], terminal=artifact), *output.columns[1:]),
            "COLUMNS",
        ),
    ):
        with pytest.raises(ValueError, match="^OUTPUT_%s$" % code):
            verify_output(replace(output, columns=columns), artifact, output.contract)
    # Coordinated native description cannot certify a corrupted original range.
    real = output.columns[1].realization
    saved = dict(real.domain)
    try:
        real.domain["max"] = "9223372036854775807"
        with pytest.raises(
            ValueError,
            match="^Emission inspection requires a verified artifact: plan_ast_correspondence$",
        ):
            bind_postgres_output(output, metadata)
    finally:
        real.domain.clear()
        real.domain.update(saved)


def test_outer_join_and_set_have_result_authority(tmp_path):
    outer = prepare_output(
        build(tmp_path / "join", "postgres", "W_join_values", "left_marker").artifact
    )
    nullable = outer.columns[1]
    assert nullable.realization.nullable is True
    assert nullable.source_field is not None
    selected = prepare_output(
        build(tmp_path / "set", "postgres", "S_set_forms", "union_all").artifact
    )
    assert selected.columns[0].source_field is None
    assert len(selected.columns[0].original.inputs) == 2
    with pytest.raises(ResultError, match="^OUTPUT_INVENTORY$"):
        verify_output(
            replace(outer, units=selected.units), outer.artifact, outer.contract
        )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("precision", (39, 65))
@pytest.mark.parametrize("state", ("values", "empty", "null"))
def test_seven_scalar_original_meanings(tmp_path, target, precision, state):
    from _pietto_phase68_slice5_cases import seven_artifact

    output = prepare_output(
        seven_artifact(tmp_path / "compiled", target, precision=precision, state=state)
    )
    assert {c.realization.tag for c in output.columns} == {
        "Int",
        "Bool",
        "Float",
        "Text",
        "Decimal",
        "Timestamp",
        "UUID",
    }
    for column in output.columns[:4]:
        assert column.field.meaning is not None
        assert column.field.meaning.source_port.field is column.source_field.field


def test_value_sensitive_fact_root_and_same_type_swap(tmp_path):
    import _pietto_phase67_result_product_probe as product
    from _pietto_phase68_slice4_probe import template
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_execution import (
        prepare_bound_execution,
        PostgresAccess,
    )

    source = product.source("postgres").replace("renamed = id", "renamed = id + 1")
    t = template(tmp_path / "template", source, lower=-10, upper=10)
    a = bind_values(t, ((t.slots[0], 1),))
    b = bind_values(t, ((t.slots[0], 5),))
    output = prepare_output(a.artifact, binding=a)
    access = PostgresAccess(
        "127.0.0.1", 5432, "test", "pietto_query", "private", "disable"
    )
    with pytest.raises(ValueError, match="^ROOT$"):
        prepare_bound_execution(b, access, output=output)
    assert (
        prepare_output(b.artifact, binding=b).columns[0].realization.domain["max"]
        == "15"
    )
    with pytest.raises(ValueError, match="^OUTPUT_COLUMNS$"):
        verify_output(
            replace(output, columns=output.columns[::-1]),
            a.artifact,
            output.contract,
            binding=a,
        )


@pytest.mark.parametrize(
    "case,variant,damage",
    (
        ("X_aggregate_global", "bag", "count"),
        ("W_join_values", "left_marker", "outer"),
        ("S_set_forms", "union_all", "set"),
    ),
)
def test_family_authority_cannot_be_replaced_by_matching_shape(
    tmp_path, case, variant, damage
):
    output = prepare_output(build(tmp_path, "postgres", case, variant).artifact)
    if damage == "count":
        column = next(
            c for c in output.columns if c.realization.domain.get("min") == "0"
        )
        column.realization.domain["max"] = "10"
    elif damage == "outer":
        object.__setattr__(output.columns[1].realization, "nullable", False)
    else:
        original = output.columns[0].original
        object.__setattr__(original, "inputs", original.inputs[::-1])
    with pytest.raises(
        ValueError,
        match="^Emission inspection requires a verified artifact: plan_ast_correspondence$",
    ):
        verify_output(output, output.artifact, output.contract)
