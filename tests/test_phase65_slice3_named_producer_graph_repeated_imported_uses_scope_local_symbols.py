"""Real named graphs and use-local binding witnesses without JOIN/SET planning."""

from pathlib import Path
from pietto.ast_nodes import LiteralExpr

import pytest

from pietto._project.project_sql_plan import ProjectSQLPlan, build_project_sql_plan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
    _roots,
    _source,
)


def _chain(kind: str = "table", family: str = "postgres") -> str:
    base = _source(family=family).split("query result:", 1)[0]
    return (
        base
        + f"""{kind} first:
    from rows
    select:
        a = name
        b = name
        key = id
table second:
    from first
    select:
        renamed = b
        id = key
query result:
    from second
    select:
        id
        value = renamed
"""
    )


@pytest.mark.parametrize("kind", ("table", "query"))
@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_named_chain_uses_immediate_exports(
    tmp_path: Path, kind: str, family: str
) -> None:
    roots = _roots(tmp_path, _chain(kind, family))
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    verified = verify_project_sql_plan(plan, *roots)
    assert verified.verified, verified.issues
    view = inspect_project_sql_plan(verified)
    assert [b.selected.owner.definition.name for b in view.blocks] == [
        "first",
        "second",
        "result",
    ]
    assert [p.identity.name for p in view.exports] == ["id", "value"]
    assert len(view.all_exports) == 7
    assert len(view.input_uses) == 3
    assert len(view.demands) == 8


def _binding_product(roots):
    from pietto._project.project_sql_plan import (
        ProjectSQLBindings,
        build_project_sql_bindings,
    )

    from pietto._project.project_sql_plan_verification import (
        verify_project_sql_bindings,
    )
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_bindings

    bindings = build_project_sql_bindings(*roots)
    assert isinstance(bindings, ProjectSQLBindings)
    verified = verify_project_sql_bindings(bindings, *roots)
    assert verified.verified, verified.issues
    return bindings, inspect_project_sql_bindings(verified)


def _repeated_sets(depth: int = 12) -> str:
    text = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
table p0:
    from rows
    select:
        id
"""
    text += "".join(
        f"table p{i}:\n    union all:\n        from p{i - 1}\n        from p{i - 1}\n"
        for i in range(1, depth + 1)
    )
    return text + f"query result:\n    from p{depth}\n    select:\n        id\n"


def test_depth12_repeated_set_binding_is_not_whole_plan(
    tmp_path: Path, record_property
) -> None:
    from time import perf_counter
    from pietto._project.project_sql_plan import (
        ProjectSQLPlanUnavailable,
        ProjectSQLSymbolNamespace,
    )
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedSetOperationOutput,
        ProjectIRCompletedQueryBlockOutput,
    )

    started = perf_counter()
    roots = _roots(tmp_path, _repeated_sets())
    upstream_seconds = perf_counter() - started
    assert roots[0].ok, roots[0].diagnostics
    started = perf_counter()
    bindings, view = _binding_product(roots)
    record_property("upstream_seconds", upstream_seconds)
    record_property("binding_and_verification_seconds", perf_counter() - started)
    named = tuple(
        d for d in view.definitions if d.entry.owner.definition.name.startswith("p")
    )
    uses = tuple(
        u for u in view.input_uses if any(u.consumer is d.ref for d in named[1:])
    )
    assert len(named) == 13 and len(uses) == 24
    assert len(view.definitions) == 15 and len(view.input_uses) == 26
    assert len(view.demands) == 15
    assert isinstance(named[-1].entry, ProjectIRCompletedSetOperationOutput)
    assert isinstance(view.definitions[-1].entry, ProjectIRCompletedQueryBlockOutput)
    for i in range(1, 13):
        pair = tuple(u for u in uses if u.consumer is named[i].ref)
        assert len(pair) == 2 and pair[0] is not pair[1]
        assert pair[0].producer is pair[1].producer is named[i - 1].ref
        assert pair[0].ports[0] is not pair[1].ports[0]
        assert (
            pair[0].ports[0].field
            is pair[1].ports[0].field
            is named[i - 1].exports[0].field
        )
        assert (
            pair[0].ports[0].producer_port
            is pair[1].ports[0].producer_port
            is named[i - 1].exports[0].ref
        )
        symbols = tuple(
            s
            for s in view.symbols
            if s.scope is named[i].ref
            and s.namespace is ProjectSQLSymbolNamespace.RELATION_USE
        )
        assert len(symbols) == 2 and symbols[0].ref is not symbols[1].ref
        context = view.context(named[i].ref)
        assert tuple(context.lookup(s.ref) for s in symbols) == pair
    assert bindings.scope.analysis_bundle is roots[1]
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert sum(b.kind.value == "set_operation" for b in result.blockers) == 12
    checked = verify_project_sql_plan(result, *roots)
    assert not checked.verified
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(checked)


@pytest.mark.parametrize("mixed", (False, True))
def test_real_join_repeated_or_mixed_inputs_have_distinct_scoped_symbols(
    tmp_path: Path, mixed: bool
) -> None:
    from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
        _source as join_source,
    )
    from pietto._project.project_sql_plan import (
        ProjectSQLPlanUnavailable,
        ProjectSQLSymbolNamespace,
    )

    text = join_source("lhs.id == r.id")
    if mixed:
        text = text.replace('postgres.table("rhs")', 'mysql.table("lhs")')
    else:
        text = text.replace("join rhs as r:", "join lhs as r:")
    roots = _roots(tmp_path, text)
    assert roots[0].ok
    bindings, view = _binding_product(roots)
    assert len(view.input_uses) == 2
    lhs, rhs = view.input_uses
    assert (lhs.producer is rhs.producer) is not mixed
    assert lhs.edge is not rhs.edge and lhs.ports[0] is not rhs.ports[0]
    assert len(view.sources) == (2 if mixed else 1)
    context = view.context(lhs.consumer)
    relations = tuple(
        s
        for s in view.symbols
        if s.scope is lhs.consumer
        and s.namespace is ProjectSQLSymbolNamespace.RELATION_USE
    )
    assert [s.label for s in relations] == ["lhs", "r"]
    assert context.lookup(relations[0].ref) is lhs
    assert context.lookup(relations[1].ref) is rhs
    if mixed:
        left_literal, right_literal = (
            source.connector.arguments[0] for source in view.sources
        )
        assert isinstance(left_literal, LiteralExpr) and isinstance(
            right_literal, LiteralExpr
        )
        assert left_literal.value == right_literal.value
        assert view.sources[0].declaration is not view.sources[1].declaration
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert any(b.kind.value == "join" for b in result.blockers)


def test_imported_reexported_producer_keeps_defining_module_and_exact_trail(
    tmp_path: Path,
) -> None:
    from pietto._project.project_sql_plan import ProjectSQLSymbolNamespace

    original = _chain().split("table second:", 1)[0]
    (tmp_path / "a.pietto").write_text(original + "export:\n    table first\n")
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n'
    )
    roots = _roots(
        tmp_path,
        """import "b.pietto":
    table Public as Alias
query result:
    from Alias
    select:
        id = key
        label = b
""",
    )
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    view = inspect_project_sql_plan(checked)
    use = next(u for u in view.input_uses if u.dependency.consumer is roots[2])
    assert use.binding.imported_binding is not None
    assert use.origin_path is next(
        o
        for o in roots[1].root.base_plan.attribution.origins
        if o.import_occurrence is not None and o.owning_module_path == "main.pietto"
    )
    assert len(use.origin_path.hops) == 2
    assert [h.facade_occurrence.owning_module_path for h in use.origin_path.hops] == [
        "b.pietto",
        "a.pietto",
    ]
    assert (
        view.sources[0].module.path
        == view.sources[0].declaration.span.path
        == "a.pietto"
    )
    symbol = next(s for s in view.symbols if s.subject is use.ref)
    assert (
        symbol.label == "Alias"
        and symbol.namespace is ProjectSQLSymbolNamespace.RELATION_USE
    )
    assert view.context(use.consumer).lookup(symbol.ref) is use
    assert [p.identity.name for p in view.exports] == ["id", "label"]
    assert len(view.intermediate_exports) == 3


def test_two_import_paths_share_definition_but_not_binding(tmp_path: Path) -> None:
    from pietto._project.project_sql_plan import ProjectSQLPlanUnavailable

    (tmp_path / "a.pietto").write_text(
        _chain().split("table second:", 1)[0] + "export:\n    table first\n"
    )
    for facade in ("b", "c"):
        (tmp_path / f"{facade}.pietto").write_text(
            'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n'
        )
    roots = _roots(
        tmp_path,
        """import "b.pietto":
    table Public as Left
import "c.pietto":
    table Public as Right
query result:
    union all:
        from Left
        from Right
""",
    )
    assert roots[0].ok
    _, view = _binding_product(roots)
    pair = tuple(u for u in view.input_uses if u.dependency.consumer is roots[2])
    assert len(pair) == 2 and pair[0].producer is pair[1].producer
    assert pair[0].binding is not pair[1].binding
    assert pair[0].origin_path is not pair[1].origin_path
    assert [
        u.origin_path.hops[0].facade_occurrence.owning_module_path for u in pair
    ] == ["b.pietto", "c.pietto"]
    assert len(view.definitions) == 3
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


def test_labels_do_not_create_cross_scope_or_namespace_identity(tmp_path: Path) -> None:
    from pietto._project.project_sql_plan import ProjectSQLSymbolNamespace

    roots = _roots(
        tmp_path,
        _chain()
        .replace("a = name", "A = name")
        .replace("b = name", "a = name")
        .replace("renamed = b", "renamed = a"),
    )
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    view = inspect_project_sql_plan(verify_project_sql_plan(plan, *roots))
    first, second = view.blocks[:2]
    own = tuple(s for s in view.symbols if s.scope is first.ref)
    foreign = tuple(s for s in view.symbols if s.scope is second.ref)
    assert any(s.label == "A" for s in own) and any(s.label == "a" for s in own)
    for symbol in own:
        subject = view.context(first.ref).lookup(symbol.ref)
        assert subject.ref is symbol.subject
    for symbol in foreign:
        with pytest.raises(ValueError, match="scope"):
            view.context(first.ref).lookup(symbol.ref)
    for scope in (first.ref, second.ref):
        for namespace in ProjectSQLSymbolNamespace:
            selected = tuple(
                s for s in view.symbols if s.scope is scope and s.namespace is namespace
            )
            assert [s.position for s in selected] == list(range(len(selected)))


@pytest.fixture(scope="module")
def bound_graphs(tmp_path_factory: pytest.TempPathFactory):
    roots = tuple(
        _roots(tmp_path_factory.mktemp("named-graph"), _chain()) for _ in range(2)
    )
    pairs = tuple(_binding_product(r) for r in roots)
    return roots, pairs


@pytest.mark.parametrize(
    "section",
    (
        "definitions",
        "sources",
        "input_uses",
        "source_ports",
        "input_ports",
        "all_exports",
        "boundaries",
        "symbols",
        "origins",
        "demands",
    ),
)
@pytest.mark.parametrize("change", ("omit", "extra", "reorder", "foreign"))
def test_binding_inventories_are_complete_and_root_exact(
    bound_graphs, section: str, change: str
) -> None:
    from pietto._project.project_sql_plan_verification import (
        verify_project_sql_bindings,
    )
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_bindings
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )

    roots, ((bindings, _), (foreign, _)) = bound_graphs
    original = getattr(bindings, section)
    changed = {
        "omit": original[1:],
        "extra": (*original, original[0]),
        "reorder": tuple(reversed(original))
        if len(original) > 1
        else (*original, original[0]),
        "foreign": getattr(foreign, section),
    }[change]
    result = verify_project_sql_bindings(
        _graft(bindings, **{section: changed}), *roots[0]
    )
    assert not result.verified, (section, change)
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_bindings(result)


@pytest.mark.parametrize(
    "mutation",
    (
        "definition_entry",
        "definition_duplicate",
        "definition_exports",
        "immediate_producer",
        "use_edge",
        "use_binding",
        "alias_graft",
        "import_origin",
        "input_image",
        "field_identity",
        "port_scope",
        "symbol_capture",
        "symbol_collision",
        "symbol_role",
        "symbol_label",
        "boundary_reason",
        "cycle",
        "intermediate_demand",
        "intermediate_origin",
    ),
)
def test_field_level_named_binding_mutations(bound_graphs, mutation: str) -> None:
    from dataclasses import replace
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundaryReason,
        ProjectSQLSymbolNamespace,
        ProjectSQLOriginRole,
    )
    from pietto._project.project_sql_plan_verification import (
        verify_project_sql_bindings,
    )
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )

    roots, ((bindings, _), (foreign, _)) = bound_graphs
    d, u, s = bindings.definitions, bindings.input_uses, bindings.symbols
    last = u[-1]
    port = last.ports[0]
    last_symbol = next(x for x in s if x.subject is port.ref)

    def replace_symbol(value):
        return tuple(value if x is last_symbol else x for x in s)

    updates = {
        "definition_entry": (
            "definitions",
            (_graft(d[0], entry=foreign.definitions[0].entry), *d[1:]),
        ),
        "definition_duplicate": ("definitions", (d[0], d[0], *d[2:])),
        "definition_exports": (
            "definitions",
            (d[0], _graft(d[1], exports=d[1].exports[1:]), *d[2:]),
        ),
        "immediate_producer": (
            "input_uses",
            (*u[:-1], _graft(last, producer=d[0].ref)),
        ),
        "use_edge": (
            "input_uses",
            (*u[:-1], _graft(last, edge=foreign.input_uses[-1].edge)),
        ),
        "use_binding": (
            "input_uses",
            (*u[:-1], _graft(last, binding=foreign.input_uses[-1].binding)),
        ),
        "alias_graft": (
            "input_uses",
            (*u[:-1], _graft(last, binding=_graft(last.binding, local_name="first"))),
        ),
        "import_origin": (
            "input_uses",
            (*u[:-1], _graft(last, origin_path=replace(last.origin_path))),
        ),
        "input_image": (
            "input_uses",
            (
                *u[:-1],
                _graft(
                    last,
                    ports=(
                        _graft(port, producer_port=d[0].exports[0].ref),
                        *last.ports[1:],
                    ),
                ),
            ),
        ),
        "field_identity": (
            "input_uses",
            (
                *u[:-1],
                _graft(
                    last,
                    ports=(
                        _graft(port, identity=d[0].exports[0].identity),
                        *last.ports[1:],
                    ),
                ),
            ),
        ),
        "port_scope": (
            "input_uses",
            (
                *u[:-1],
                _graft(last, ports=(_graft(port, owner=u[0].ref), *last.ports[1:])),
            ),
        ),
        "symbol_capture": (
            "symbols",
            replace_symbol(_graft(last_symbol, scope=d[0].ref)),
        ),
        "symbol_collision": (
            "symbols",
            replace_symbol(
                _graft(
                    last_symbol,
                    position=next(
                        x.position
                        for x in s
                        if x.scope is last_symbol.scope
                        and x.namespace is last_symbol.namespace
                        and x is not last_symbol
                    ),
                )
            ),
        ),
        "symbol_role": (
            "symbols",
            replace_symbol(
                _graft(last_symbol, namespace=ProjectSQLSymbolNamespace.RELATION_USE)
            ),
        ),
        "symbol_label": ("symbols", replace_symbol(_graft(last_symbol, label="wrong"))),
        "boundary_reason": (
            "boundaries",
            (
                bindings.boundaries[0],
                _graft(
                    bindings.boundaries[1], reason=ProjectSQLBoundaryReason.SOURCE_INPUT
                ),
                *bindings.boundaries[2:],
            ),
        ),
        "cycle": ("input_uses", (*u[:-1], _graft(last, producer=last.consumer))),
        "intermediate_demand": (
            "demands",
            (bindings.demands[0], *bindings.demands[2:]),
        ),
        "intermediate_origin": (
            "origins",
            tuple(
                o
                for o in bindings.origins
                if not (
                    o.subject is d[1].exports[0].ref
                    and o.role is ProjectSQLOriginRole.STAGE_EXPORT
                )
            ),
        ),
    }
    name, value = updates[mutation]
    result = verify_project_sql_bindings(_graft(bindings, **{name: value}), *roots[0])
    assert not result.verified, mutation


def test_full_plan_preserves_selected_exports_and_rejects_internal_omissions(
    tmp_path: Path,
) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )

    roots = _roots(tmp_path, _chain())
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    for bad in (
        _graft(plan, exports=plan.bindings.definitions[1].exports),
        _graft(plan, all_exports=plan.exports),
        _graft(plan, blocks=plan.blocks[1:]),
        _graft(plan, projections=plan.projections[1:]),
        _graft(plan, demands=plan.demands[-2:]),
    ):
        assert not verify_project_sql_plan(bad, *roots).verified
    uses = {u.ref: u for u in plan.input_uses}
    definitions = {d.ref: d for d in plan.bindings.definitions}
    ports = {p.ref: p for p in plan.input_ports}
    for projection in plan.projections:
        use = uses[projection.input_use]
        producer = definitions[use.producer]
        port = ports[projection.input_port]
        assert any(
            projection.source_port is p.ref and port.field is p.field
            for p in producer.exports
        )
        assert projection.symbol.scope is projection.block
    assert plan.exports is plan.bindings.definitions[-1].exports


def test_unsupported_named_ancestor_and_unrelated_sibling_are_distinguished(
    tmp_path: Path,
) -> None:
    from pietto._project.project_sql_plan import ProjectSQLPlanUnavailable

    for reached in (False, True):
        source = _chain()
        if reached:
            source = source.replace(
                "    from rows\n    select:",
                "    from rows\n    where id > 0\n    select:",
            )
        else:
            source += "query unused:\n    from rows\n    where id > 0\n    select:\n        id\n"
        roots = _roots(tmp_path / str(reached), source)
        assert roots[0].ok
        result = build_project_sql_plan(*roots)
        if reached:
            assert isinstance(result, ProjectSQLPlanUnavailable)
            assert [
                (b.owner.definition.name, b.kind.value) for b in result.blockers
            ] == [("first", "where"), ("first", "ir_stage")]
        else:
            assert isinstance(result, ProjectSQLPlan)
            assert verify_project_sql_plan(result, *roots).verified


def test_binding_verifier_and_context_do_not_call_allocators(
    bound_graphs, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pietto._project.project_sql_plan as planning
    from pietto._project.project_sql_plan_verification import (
        verify_project_sql_bindings,
    )
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_bindings

    roots, ((bindings, _), _) = bound_graphs

    def forbidden(*args, **kwargs):
        raise AssertionError("verification must not allocate expected bindings")

    monkeypatch.setattr(planning, "build_project_sql_bindings", forbidden)
    monkeypatch.setattr(planning, "build_project_sql_plan", forbidden)
    result = verify_project_sql_bindings(bindings, *roots[0])
    assert result.verified
    view = inspect_project_sql_bindings(result)
    for symbol in view.symbols:
        assert view.context(symbol.scope).lookup(symbol.ref).ref is symbol.subject


def test_shared_producer_has_independent_uses_in_separate_consumers(
    tmp_path: Path,
) -> None:
    source = (
        _chain().split("table second:", 1)[0]
        + """table branch_a:
    from first
    select:
        id = key
table branch_b:
    from first
    select:
        id = key
query result:
    union all:
        from branch_a
        from branch_b
"""
    )
    roots = _roots(tmp_path, source)
    assert roots[0].ok
    _, view = _binding_product(roots)
    shared = next(
        d for d in view.definitions if d.entry.owner.definition.name == "first"
    )
    pair = tuple(u for u in view.input_uses if u.producer is shared.ref)
    assert len(pair) == 2 and pair[0].consumer is not pair[1].consumer
    assert (
        pair[0].ports[0].producer_port
        is pair[1].ports[0].producer_port
        is shared.exports[0].ref
    )
    symbols = tuple(next(s for s in view.symbols if s.subject is u.ref) for u in pair)
    assert symbols[0].label == symbols[1].label == "first"
    for use, symbol in zip(pair, symbols, strict=True):
        assert view.context(use.consumer).lookup(symbol.ref) is use
    with pytest.raises(ValueError, match="scope"):
        view.context(pair[0].consumer).lookup(symbols[1].ref)


def test_binding_verification_is_invalidated_by_grafts(bound_graphs) -> None:
    from pietto._project.project_sql_plan_verification import (
        verify_project_sql_bindings,
    )
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_bindings
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )

    roots, ((bindings, _), (foreign, _)) = bound_graphs
    assert not verify_project_sql_bindings(bindings, *roots[1]).verified
    checked = verify_project_sql_bindings(bindings, *roots[0])
    for bad in (
        _graft(bindings, demands=()),
        _graft(bindings, definitions=foreign.definitions),
    ):
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_bindings(_graft(checked, bindings=bad))


def test_import_provenance_and_defining_source_cannot_be_grafted(
    tmp_path: Path,
) -> None:
    from pietto._project.project_sql_plan_verification import (
        verify_project_sql_bindings,
    )
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )

    (tmp_path / "a.pietto").write_text(
        _source().split("query result:")[0] + "export:\n    source rows\n"
    )
    roots = _roots(
        tmp_path,
        'import "a.pietto":\n    source rows as local\nquery result:\n    from local\n    select:\n        id\n',
    )
    assert roots[0].ok
    bindings, _ = _binding_product(roots)
    use = bindings.input_uses[0]
    assert use.origin_path.hops and use.binding.imported_binding is not None
    missing_path = _graft(bindings, input_uses=(_graft(use, origin_path=None),))
    missing_import = _graft(
        bindings,
        input_uses=(_graft(use, binding=_graft(use.binding, imported_binding=None)),),
    )
    wrong_module = _graft(
        bindings,
        sources=(
            _graft(
                bindings.sources[0],
                module=roots[0].semantic_result.modules[roots[2].module_position],
            ),
        ),
    )
    for bad in (missing_path, missing_import, wrong_module):
        assert not verify_project_sql_bindings(bad, *roots).verified


@pytest.mark.parametrize("graft", ("historical_consumer", "active_properties"))
def test_binding_admission_rejects_incoherent_current_input_evidence(
    tmp_path: Path, graft: str
) -> None:
    from pietto._project.project_sql_plan import build_project_sql_bindings
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedQueryBlockOutput,
    )
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )

    roots = _roots(
        tmp_path, _chain() if graft == "historical_consumer" else _repeated_sets(1)
    )
    assert roots[0].ok
    root = roots[1].root
    if graft == "historical_consumer":
        owner = root.base_plan
        attribute = "cross_relation_edges"
        original = owner.cross_relation_edges
        edge = original[0]
        replacement = (_graft(edge, consumer=_graft(edge.consumer)), *original[1:])
    else:
        owner = root.entries[-1]
        assert isinstance(owner, ProjectIRCompletedQueryBlockOutput)
        attribute = "relation_input"
        original = owner.relation_input
        assert original is not None
        replacement = _graft(original, producer=_graft(original.producer))
    object.__setattr__(owner, attribute, replacement)
    try:
        with pytest.raises(ValueError, match="exact|active"):
            build_project_sql_bindings(*roots)
    finally:
        object.__setattr__(owner, attribute, original)
