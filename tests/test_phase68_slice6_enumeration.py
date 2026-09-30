"""Independent finite three-valued truth and structural ordering witnesses."""

from dataclasses import replace
from itertools import product

import pytest

from pietto._project.project_refinement_order import (
    before,
    check_coordinates,
    compare,
    integer_coordinate,
)
from pietto._project.project_refinement_rendering import null_equal, ref


def sql_truth(expression, row):
    kind, arguments = expression.kind, expression.args
    if kind == "ref":
        return row[arguments]
    if kind == "integer":
        return arguments[0]
    values = [sql_truth(a, row) for a in arguments]
    if kind == "is_null":
        return values[0] is None
    if kind == "is_not_null":
        return values[0] is not None
    if kind == "and":
        return False if False in values else None if None in values else True
    if kind == "or":
        return True if True in values else None if None in values else False
    if kind == "not":
        return None if values[0] is None else not values[0]
    if None in values:
        return None
    a, b = values
    return {"=": a == b, "<": a < b, ">": a > b}[kind]


def test_null_equality_is_two_valued_before_exclusion():
    expression = null_equal(ref("a", "v"), ref("b", "v"))
    for a, b in product((None, -1, 0, 1), repeat=2):
        assert sql_truth(expression, {("a", "v"): a, ("b", "v"): b}) is (a == b)


@pytest.mark.parametrize(
    "family,direction,ordered",
    (
        ("postgres", "asc", (-1, 0, 1, None)),
        ("postgres", "desc", (None, 1, 0, -1)),
        ("mysql", "asc", (None, -1, 0, 1)),
        ("mysql", "desc", (1, 0, -1, None)),
    ),
)
def test_native_and_client_comparators_match_literal_order(family, direction, ordered):
    coordinate = replace(integer_coordinate(("test",), -1, 1), nullable=True)
    expression = before((ref("a", "v"),), (ref("b", "v"),), (direction,), family)
    for i, a in enumerate(ordered):
        for j, b in enumerate(ordered):
            assert sql_truth(expression, {("a", "v"): a, ("b", "v"): b}) is (i < j)
            assert compare((a,), (b,), (coordinate,), (direction,), family) == (
                -1 if i < j else 0 if i == j else 1
            )


def test_mixed_direction_nullable_tuple_has_no_unknown_holes():
    ordered = ((0, None), (0, 1), (0, 0), (None, None), (None, 1), (None, 0))
    coordinate = replace(integer_coordinate(("test",), 0, 1), nullable=True)
    expression = before(
        tuple(ref("a", n) for n in ("x", "y")),
        tuple(ref("b", n) for n in ("x", "y")),
        ("asc", "desc"),
        "postgres",
    )
    for i, a in enumerate(ordered):
        for j, b in enumerate(ordered):
            row = {
                ("a", "x"): a[0],
                ("a", "y"): a[1],
                ("b", "x"): b[0],
                ("b", "y"): b[1],
            }
            assert sql_truth(expression, row) is (i < j)
            assert compare(
                a, b, (coordinate, coordinate), ("asc", "desc"), "postgres"
            ) == (-1 if i < j else 0 if i == j else 1)


def test_absence_is_explicit_and_never_a_payload_null():
    presence = integer_coordinate(("presence",), 0, 1)
    key = replace(integer_coordinate(("key",)), active=((0, 1),))
    assert check_coordinates((0, None), (presence, key)) == (0, None)
    assert check_coordinates((1, 0), (presence, key)) == (1, 0)
    for values in ((0, 3), (1, None), (True, 0), (1, 0.0), (2, 0)):
        with pytest.raises(ValueError):
            check_coordinates(values, (presence, key))


@pytest.fixture
def page_query(tmp_path):
    from _pietto_phase66_sql_emission_probe import fixture, build_case
    from test_phase68_slice6_refinement import capabilities
    from pietto._project.project_refinement import TieRefinement, prepare_refinement

    base = fixture("postgres")
    source = (
        base["source"].split("table result:", 1)[0]
        + "table result:\n    from rows\n    select:\n        id\n"
    )
    _, result = build_case(tmp_path, source, base["contract"])
    assert result.status == "VERIFIED"
    return prepare_refinement(
        result.artifact, capabilities(result.artifact), policy=TieRefinement()
    )


def observed_enumerator(query, *, size=2, environment=None):
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project.project_execution_source import (
        ObservedSource,
        admit_observed_sources,
    )
    from pietto._project.project_refinement_enumeration import Enumeration
    from pietto._project.project_result_output import source_read_columns

    req = query.sources[0]
    reads = source_read_columns(query.output)
    observation = ObservedSource(
        req,
        "postgres_rows",
        41,
        req.role,
        ((req.provider, req.version, 1, req.revision),),
        req.definition,
        (20,),
        (),
        (("__pietto_source_0", 20, None, 8, None, None, None),),
        (),
        ("NORMAL",) * 6,
    )
    admission = admit_observed_sources(
        query.sources,
        reads,
        (observation,),
        route="postgres_rows",
        session_id=41,
        role=req.role,
        environment=environment or ("18.6", "repeatable read", True, "UTF8"),
    )
    return Enumeration(query, admission, limits=ExecutionLimits(batch_rows=size))


def page_metadata(query):
    from types import SimpleNamespace

    names = (query.output.columns[0].label,) + query.units[-1].key_names
    return tuple(
        SimpleNamespace(name=n, type_code=20, null_ok=None, precision=None, scale=None)
        for n in names
    )


def test_full_page_is_not_eof_and_equal_payload_copies_survive(page_query):
    stream = observed_enumerator(page_query)
    page = stream.request_page()
    assert page.native.arguments == (2,)
    checked = stream.check_page(
        page, page_metadata(page_query), ((7, 0, 1), (7, 0, 2)), terminal="NORMAL"
    )
    assert checked.rows == ((7,), (7,)) and checked.complete is False
    assert stream.progress == (0, 0, False, False)
    stream.commit_page(checked)
    assert stream.progress == (2, 1, False, False)
    continuation = stream.request_page()
    assert continuation.native.arguments == (0, 2, 2)
    assert b" WHERE " in continuation.native.sql
    checked = stream.check_page(
        continuation, page_metadata(page_query), (), terminal="NORMAL"
    )
    stream.commit_page(checked)
    assert stream.progress == (2, 2, True, False)
    with pytest.raises(ValueError, match="PAGE_LIFETIME"):
        stream.request_page()


@pytest.mark.parametrize(
    "damage",
    (
        "foreign_page",
        "overlap",
        "key_null",
        "not_eof",
        "extra_field",
        "metadata",
        "foreign_frontier",
    ),
)
def test_bad_pages_do_not_advance(page_query, damage):
    stream = observed_enumerator(page_query)
    page = stream.request_page()
    rows = ((7, 0, 1), (8, 0, 2))
    metadata = page_metadata(page_query)
    terminal = "NORMAL"
    if damage == "foreign_page":
        page = replace(page)
    elif damage == "overlap":
        rows = ((7, 0, 1), (8, 0, 1))
    elif damage == "key_null":
        rows = ((7, 0, None),)
    elif damage == "not_eof":
        terminal = "UNKNOWN"
    elif damage == "extra_field":
        rows = ((7, 0, 1, 9),)
    elif damage == "metadata":
        metadata = metadata[::-1]
    else:
        object.__setattr__(page, "frontier", (0, 900))
    with pytest.raises(ValueError):
        stream.check_page(page, metadata, rows, terminal=terminal)
    assert stream.progress == (0, 0, False, True)


def test_arbitrary_internal_frontier_is_not_completed_prefix(page_query):
    stream = observed_enumerator(page_query)
    stream._frontier = (0, 999)
    with pytest.raises(ValueError, match="PROGRESS_CHANGED"):
        stream.request_page()
    assert stream.progress[:2] == (0, 0)


@pytest.mark.parametrize(
    "mode", ("cancel", "deadline", "changed_policy", "changed_result")
)
def test_last_acceptance_checkpoint_rejects_late_changes(page_query, mode):
    import threading
    import time
    from pietto._project.project_refinement import TieRefinement

    stream = observed_enumerator(page_query)
    page = stream.request_page()
    checked = stream.check_page(
        page, page_metadata(page_query), ((7, 0, 1),), terminal="NORMAL"
    )
    options = {}
    if mode == "cancel":
        event = threading.Event()
        event.set()
        options["cancel_event"] = event
    elif mode == "deadline":
        options["deadline"] = time.monotonic() - 1
    elif mode == "changed_policy":
        object.__setattr__(page_query, "policy", TieRefinement())
    else:
        object.__setattr__(checked, "complete", 1)
    with pytest.raises((ValueError, TimeoutError)):
        stream.commit_page(checked, **options)
    assert stream.progress == (0, 0, False, True)


@pytest.mark.parametrize(
    "environment",
    (
        ("18.5", "repeatable read", True, "UTF8"),
        ("18.6", "read committed", True, "UTF8"),
        ("18.6", "repeatable read", False, "UTF8"),
        ("18.6", "repeatable read", True, "LATIN1"),
    ),
)
def test_wrong_native_environment_cannot_start_pages(page_query, environment):
    with pytest.raises(ValueError, match="ENVIRONMENT"):
        observed_enumerator(page_query, environment=environment)


def test_decimal_coordinate_extreme_exponent_is_checked_without_large_power():
    from decimal import Decimal
    from pietto._project.project_refinement_order import Coordinate, check_value

    coordinate = Coordinate(
        ("decimal",),
        "Decimal",
        False,
        (("precision", 65), ("scale", 30)),
        (("kind", "pg_numeric"),),
    )
    assert check_value(Decimal("0E-999999999"), coordinate) == 0
    assert check_value(Decimal("1.2300"), coordinate) == Decimal("1.23")
    for value in (Decimal("1E-999999999"), Decimal("1E999999999"), Decimal("NaN")):
        with pytest.raises(ValueError):
            check_value(value, coordinate)
