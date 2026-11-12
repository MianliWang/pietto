"""Editor overlays: a project check reads an open buffer in place of its file,
and emission, compiled builds and package code refuse that buffer by type."""

from __future__ import annotations

import contextlib
import functools
import io
import json
from pathlib import Path

import pytest

import _pietto_project_package as package
import _pietto_sql_emission as probe
from pietto import cli
from pietto._project import (
    check,
    package_graph,
    project_compiled_build,
    project_sql_emission_cli as emission_cli,
    project_sql_emission_contract,
)
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.package_graph import PackageGraphOutcome, _build_package_graph
from pietto._project.package_inspection import _build_package_inspection_fact_set
from pietto._project.project_sql_emission_cli import emit_project
from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
from pietto._project.trusted_source import (
    ProjectOverlaySource,
    ProjectSource,
    ProjectTrustedSourceSnapshot,
)
from pietto.errors import SourceLocation

TOML = 'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
MODELS = """shape User:
    id: UUID
    email: Text | None
    deleted_at: Timestamp | None

source users: User = postgres.table("public.users")

export (
    shape User,
    source users,
)
"""
A_OK = """from "models.pietto" import (
    source users,
)

table active_users:
    from users
    where deleted_at is None
    select:
        id
        email
"""
A_BAD = A_OK.replace("where deleted_at is None", "where nope_a is None")


def _project(tmp_path: Path, **sources: str) -> Path:
    root = tmp_path / "harbor"
    root.mkdir()
    (root / "pietto.toml").write_text(TOML, encoding="utf-8")
    # Byte-exact on every platform, as the tests compare the texts read.
    for name, text in sources.items():
        (root / f"{name}.pietto").write_text(text, encoding="utf-8", newline="\n")
    return root


def _cli_json(root: Path) -> dict[str, object]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli.main(["check", "--project", str(root), "--format", "json"])
    return json.loads(out.getvalue())


def test_an_overlay_replaces_only_the_read_of_its_selected_file(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, models=MODELS, a=A_OK)
    before = _report(root, {})
    assert before.errors == () and before.diagnostics == ()
    assert before.paths == ("a.pietto", "models.pietto")
    assert before.texts == {"a.pietto": A_OK, "models.pietto": MODELS}

    parsed = check.check_project_parse_only(
        root,
        overlays={"a.pietto": A_BAD, "pietto.toml": "broken", "nope.pietto": "x"},
    )
    assert [type(item) for item in parsed.trusted_source_snapshots] == [
        ProjectOverlaySource,
        ProjectTrustedSourceSnapshot,
    ]
    report = _report(root, {"a.pietto": A_BAD})
    assert [(d.code, d.location.path) for d in report.diagnostics] == [
        ("PIE-S2102", "a.pietto")
    ]
    assert report.texts["a.pietto"] == A_BAD
    # The disk is unchanged, and the CLI reads the disk.
    assert (root / "a.pietto").read_text(encoding="utf-8") == A_OK
    assert _cli_json(root)["diagnostics"] == []


def test_cli_project_checks_do_not_build_editor_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path, models=MODELS, a=A_OK)

    def unexpected(_: object) -> object:
        raise AssertionError("editor facts must stay out of the CLI check")

    monkeypatch.setattr(check, "_project_editor_facts", unexpected)
    assert _cli_json(root)["diagnostics"] == []


def test_editor_links_are_the_import_paths_the_module_graph_resolved(
    tmp_path: Path,
) -> None:
    """Each import statement of a module with facts is one link, at its path
    in the buffer checked, to the selected module the graph resolved it to:
    a statement's items do not repeat it, two statements to one module stay
    two, and a path that names no selected module leaves its module no
    facts."""

    b = """from "a.pietto" import (
    table active_users,
)

from "models.pietto" import (
    shape User,
    source users,
)

from "models.pietto" import (
    source users as again,
)
"""
    exported = A_OK + "\nexport (\n    table active_users,\n)\n"
    unresolved = 'from "nope.pietto" import (\n    shape User,\n)\n'
    root = _project(tmp_path, models=MODELS, a=exported, b="", c="")
    checked = check.check_project_editor_diagnostics(
        root, overlays={"b.pietto": b, "c.pietto": unresolved}
    )
    assert [(d.code, d.location.path) for d in checked.report.diagnostics] == [
        ("PIE-S2701", "c.pietto")
    ]
    assert sorted(checked.facts) == ["a.pietto", "b.pietto", "models.pietto"]
    assert [
        (link.location, link.target) for link in checked.facts["b.pietto"].links
    ] == [
        (SourceLocation("b.pietto", 1, 6, 1, 16), "a.pietto"),
        (SourceLocation("b.pietto", 5, 6, 5, 21), "models.pietto"),
        (SourceLocation("b.pietto", 10, 6, 10, 21), "models.pietto"),
    ]
    assert [link.target for link in checked.facts["a.pietto"].links] == [
        "models.pietto"
    ]
    assert checked.facts["models.pietto"].links == ()


def test_editor_facts_keep_each_retained_field_and_let_reference(
    tmp_path: Path,
) -> None:
    """Each name that a `let` value, `select` item or `where` reads is one
    fact when its retained candidate bucket holds one candidate: a field of a
    source, through an import alias too, defines its shape field; a field of
    a relation let has no target; a `let` defines its binding, and a FROM
    that reads a relation let defines that let. A name that inlining a def
    which reads its parameter twice, or a comparison chain's middle operand,
    copies is still one fact. A JOIN relation's reads, a def call and a
    relationship call have no fact. Once the source's shape fails, the input
    of each relation that reads it is unknown, and no name such a relation
    reads has a fact, not even a `let`."""

    models = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
shape Customer:
    id: Int
    name: Text
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
relationship order_customer(order: Order, customer: Customer):
    order.customer_id == customer.id
def double(x: Int) -> Int: return x + x

export (
    shape Order,
    shape Customer,
    source orders,
    source customers,
    relationship order_customer,
    def double,
)
"""
    reads = """from "models.pietto" import (
    source orders,
    source orders as purchases,
    source customers,
    relationship order_customer,
    def double,
)

query plain:
    from purchases
    let twice = double(amount)
    where twice > id and 1 < amount < 10
    select:
        id
        twice

query frequent:
    let counts:
        from orders
        group by:
            customer_id
        select:
            customer_id
            n = count()
    from counts
    where n > 10
    select:
        customer_id

query order_names:
    from orders
    let customer = customers
    inner join customer on order_customer(orders, customer)
    select:
        order_id = orders.id
        customer_name = customer.name
"""
    root = _project(tmp_path, models=models, a=reads)
    checked = check.check_project_editor_diagnostics(root, overlays={})
    assert list(checked.report.diagnostics) == []
    order = SourceLocation("models.pietto", 8, 1, 8, 53)
    field_id = SourceLocation("models.pietto", 2, 5, 2, 12)
    amount = SourceLocation("models.pietto", 4, 5, 4, 16)
    twice = SourceLocation("a.pietto", 11, 5, 11, 31)
    assert [
        (
            (use.location.line, use.location.column, use.location.end_column),
            use.detail,
            None if use.target is None else use.target.location,
        )
        for use in checked.facts["a.pietto"].uses
    ] == [
        ((10, 5, 19), "source orders", order),
        ((19, 9, 20), "source orders", order),
        ((25, 5, 16), "let counts", SourceLocation("a.pietto", 18, 5, 24, 24)),
        ((31, 5, 16), "source orders", order),
        ((11, 24, 30), "field amount", amount),
        ((14, 9, 11), "field id", field_id),
        ((15, 9, 14), "let twice", twice),
        ((12, 11, 16), "let twice", twice),
        ((12, 19, 21), "field id", field_id),
        ((12, 30, 36), "field amount", amount),
        (
            (23, 13, 24),
            "field customer_id",
            SourceLocation("models.pietto", 3, 5, 3, 28),
        ),
        ((28, 9, 20), "field customer_id", None),
        ((26, 11, 12), "field n", None),
    ]

    (root / "models.pietto").write_text(
        models.replace("amount: Int", "amount: Nope"), encoding="utf-8", newline="\n"
    )
    checked = check.check_project_editor_diagnostics(root, overlays={})
    assert [item.code for item in checked.report.diagnostics] == ["PIE-S2002"]
    assert [
        (use.location.line, use.location.column, use.detail)
        for use in checked.facts["a.pietto"].uses
    ] == [
        (10, 5, "source orders"),
        (19, 9, "source orders"),
        (25, 5, "let counts"),
        (31, 5, "source orders"),
    ]


def test_an_overlay_reads_a_file_the_disk_cannot_and_keeps_the_size_limit(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, models=MODELS)
    (root / "a.pietto").write_bytes(b"\xff\xfe")
    assert [e.kind.value for e in _report(root, {}).errors] == ["source_read"]
    assert _report(root, {"a.pietto": A_OK}).diagnostics == ()

    oversized = _report(root, {"a.pietto": "#" * 1_048_577})
    assert [(d.code, d.location.path) for d in oversized.diagnostics] == [
        ("PIE-P1006", "a.pietto")
    ]
    assert "a.pietto" not in oversized.texts


def test_the_report_without_overlays_is_the_cli_project_check(tmp_path: Path) -> None:
    b_bad = A_BAD.replace("active_users", "other").replace("nope_a", "nope_b")
    root = _project(tmp_path, models=MODELS, a=A_BAD, b=b_bad)
    report = _report(root, {})
    expected = _cli_json(root)["diagnostics"]
    assert isinstance(expected, list)
    assert [
        (d.code, d.location.path, d.location.line, d.location.column)
        for d in report.diagnostics
    ] == [
        (
            item["code"],
            item["location"]["path"],
            item["location"]["line"],
            item["location"]["column"],
        )
        for item in expected
    ]


def test_emission_refuses_an_overlay_by_type_even_with_the_disk_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = probe.fixture("postgres")
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    sources = probe.source_files(item["source"])
    # Byte-exact on every platform, so the overlays equal the disk text.
    for file, content in sources.items():
        (root / file).write_text(content, encoding="utf-8", newline="\n")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")

    def emit() -> tuple[str, list[str]]:
        outcome, _ = emit_project(
            root,
            "main.pietto",
            "table",
            "result",
            "postgres",
            "contract.json",
            ProjectSQLLiteralPolicy(item["policy"]),
        )
        return outcome.status, [error.message for error in outcome.cli_errors]

    assert emit() == ("VERIFIED", [])
    monkeypatch.setattr(
        emission_cli,
        "check_project_parse_only",
        functools.partial(check.check_project_parse_only, overlays=sources),
    )
    assert emit() == ("INPUT_REJECTED", ["Invalid current planning roots."])


def test_a_compiled_build_refuses_an_overlay_by_type_past_emission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = probe.fixture("postgres")
    monkeypatch.setattr(
        check,
        "check_project_parse_only",
        functools.partial(
            check.check_project_parse_only,
            overlays=probe.source_files(item["source"]),
        ),
    )
    # Without emission's own refusal, an artifact reaches the compiled build.
    monkeypatch.setattr(project_sql_emission_contract, "require_trusted_sources", _all)
    _, outcome = probe.build_case(
        tmp_path / "project", item["source"], item["contract"], item["policy"]
    )
    with pytest.raises(TypeError, match="not editor buffers"):
        project_compiled_build.build_compiled(outcome.artifact)
    monkeypatch.setattr(project_compiled_build, "require_trusted_sources", _all)
    project_compiled_build.build_compiled(outcome.artifact)


def test_a_package_graph_refuses_overlay_lineage_by_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    digest = package._write_package(tmp_path / "packages", "root")
    inspection = _build_package_inspection_fact_set(
        package._plan(tmp_path / "packages", "root", digest)
    )
    text = package._SOURCE_A.decode("utf-8")
    root = _project(tmp_path, main=text)

    def graph() -> tuple[PackageGraphOutcome, list[str]]:
        parsed = check.check_project_parse_only(root, overlays={"main.pietto": text})
        facts = build_empty_project_semantic_result(parsed)
        assert facts.module_package_identity_facts is not None
        result = _build_package_graph(
            inspection, module_identity_facts=(facts.module_package_identity_facts,)
        )
        return result.outcome, [error.message for error in result.errors]

    assert graph() == (
        PackageGraphOutcome.ERROR,
        [
            "Package graph construction failed: "
            "Project sources must be trusted reads, not editor buffers."
        ],
    )
    monkeypatch.setattr(package_graph, "require_trusted_sources", _all)
    assert graph() == (PackageGraphOutcome.SUCCESS, [])


def _all(sources: tuple[ProjectSource, ...]) -> tuple[ProjectSource, ...]:
    """`require_trusted_sources` without its refusal, to show it is the cause."""

    return sources


def _report(root: Path, overlays: dict[str, str]) -> check.ProjectDiagnosticsReport:
    return check.check_project_editor_diagnostics(root, overlays=overlays).report
