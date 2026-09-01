from __future__ import annotations

import ast
from pathlib import Path

from _pietto_repository_facts import REPOSITORY_FACTS


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md"
)
GRAMMAR = REPO_ROOT / "grammar/Pietto.g4"
AST_NODES = REPO_ROOT / "src/pietto/ast_nodes.py"
AST_BUILDER = REPO_ROOT / "src/pietto/ast_builder.py"
SEMANTIC_ANALYZER = REPO_ROOT / "src/pietto/semantic/analyzer.py"
RELATIONSHIP_SEMANTICS = REPO_ROOT / "src/pietto/semantic/relationship_metadata.py"
SEMANTIC_MODEL = REPO_ROOT / "src/pietto/semantic/model.py"
SHAPE_SEMANTICS = REPO_ROOT / "src/pietto/semantic/shapes.py"
IR_BUILDER = REPO_ROOT / "src/pietto/ir/builder.py"
IR_MODEL = REPO_ROOT / "src/pietto/ir/model.py"
PROJECT_MODEL = REPO_ROOT / "src/pietto/_project/model.py"
MODULE_CATALOG = REPO_ROOT / "src/pietto/_project/module_catalog.py"
MODULE_SEMANTIC_FACTS = (
    REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
)
PROJECT_IR_OPERATORS = REPO_ROOT / "src/pietto/_project/project_ir_operators.py"
PROJECT_ROW_KEYS = REPO_ROOT / "src/pietto/_project/project_row_keys.py"
PROJECT_VALUE_FDS = REPO_ROOT / "src/pietto/_project/project_value_fds.py"
PROJECT_GRAIN = REPO_ROOT / "src/pietto/_project/project_grain.py"
PROJECT_IR_RELATIONAL_PROPERTIES = (
    REPO_ROOT / "src/pietto/_project/project_ir_relational_properties.py"
)
PROJECT_RELATIONSHIP_MATCH_GUARANTEES = (
    REPO_ROOT / "src/pietto/_project/project_relationship_match_guarantees.py"
)

HEADINGS = (
    "Answer And Static Scope",
    "Starting Authority",
    "Audit Method And Current Source Snapshots",
    "Live Pietto Relationship Baseline",
    "Live Pietto UNIQUE Baseline",
    "Phase 61 Inherited Readiness",
    "Mature Source, Specification, And Research Dispositions",
    "Fundamental Identity, Ownership, And Visibility Laws",
    "Relationship Conditions And Paths",
    "Formal BAG And NULL Reference Semantics",
    "UNIQUE Null Policy And Constraint Evidence",
    "Typed Keys, FDs, Grain, And Coverage",
    "Directional Match Guarantees And Runtime Enforcement",
    "Canonical JOIN Region, Nulling, And Ordering",
    "Intrinsic Grain And Compact Closure Architecture",
    "Fanout, Fact Locality, Multi-Fact, And Join Shape",
    "Rejected Algorithms And Assurance Boundary",
    "Exact 16-Slice Route",
    "Exact Later-Owner Ledger",
    "Phase 62 Exit Criteria And Phase 63 Handoff",
    "Reader Closure, Changed-Path Lock, And Zero Delta",
    "Review, Gate, Publication, And Next Owner",
)

UPSTREAM_HEADS = {
    "dbt Core / Rust MetricFlow": "a59aa469f5dc41d58cccab169316d7ff8f6e51d3",
    "MetricFlow": "24c248833b27993fc23dc2ff087f4335e380356b",
    "SQLAlchemy": "004bab376fd769cb33efa128071459a0dd480eec",
    "ent": "69d5d4deb19599f129166634e09d33addcf3f2cc",
    "Apache DataFusion": "a2749598bea2e65241fdbf011a4aac95b58079a7",
    "Cube": "9d3dd45814a7fec41b6c4e23233f38bd7a1af1c2",
    "PostgreSQL": "6885b845b4ba0b7aee09daa9817703477faa3704",
    "DuckDB": "7f78ec0b3090cb6a5d8488c8dc61e752cc22cc28",
    "Hasura": "724551b9ae87845594ef0408cff0e50eb6c90dc5",
    "Beam": "77d0bca3c1cda8364d7a7cf95881cd826feed8ec",
    "Malloy": "ac860de9bc0df47b7fabbf9903303c40eea11680",
    "Apache Calcite": "cc1dcc48925699d729e8e77d08526bc3c618f704",
    "Substrait": "7b66a512014e0304a350ef6a1d4df6d1dd8cb585",
}

ROUTE = (
    (
        "1",
        "Architecture, current/mature-source audit, formal BAG/NULL semantics, semantic laws, and route lock",
    ),
    (
        "2",
        "Relationship declaration identity, endpoint roles, module-local resolution, and construction states",
    ),
    (
        "3",
        "Exact field correspondences, ON/WHERE separation, equality/null behavior, and constraint-scope boundary",
    ),
    (
        "4",
        "UNIQUE null policy, evidence trust, strict/lax row uniqueness, and candidate keys",
    ),
    ("5", "Strict/lax value-FD basis, compact indexes, and targeted closure"),
    (
        "6",
        "Factorized intrinsic grain basis, grain dependencies, optional factors, and GLOBAL grain",
    ),
    ("7", "Existing-operator key/FD/grain transfer and grain comparison"),
    (
        "8",
        "Referential coverage, MATCH SIMPLE/FULL, and directional match guarantees",
    ),
    (
        "9",
        "Explicit relationship paths, fanout/survival/null effects, and join-shape analysis",
    ),
    ("10", "Authored JOIN/traversal syntax and semantic uses"),
    (
        "11",
        "Project IR binary JOIN region, multi-input topology, null extension, and property transfer",
    ),
    (
        "12",
        "Per-aggregate fact locality, chasm detection, and multi-fact alignment",
    ),
    (
        "13",
        "Integrity/verifier, analysis invalidation, and bounded BAG/NULL semantic oracle",
    ),
    ("14", "Private inspection, winner-free query, and pure canonical boundary"),
    (
        "15",
        "Real authored E2E, Python differential compatibility, and metamorphic JOIN assurance",
    ),
    ("16", "Completion audit and Phase 63 handoff"),
)


def _read(path: Path = SPEC) -> str:
    if path.suffix == ".py":
        return REPOSITORY_FACTS.python(path).text
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _tables(section: str) -> tuple[tuple[tuple[str, ...], ...], ...]:
    tables: list[tuple[tuple[str, ...], ...]] = []
    rows: list[tuple[str, ...]] = []
    for line in (*section.splitlines(), ""):
        if line.startswith("| "):
            if not line.startswith("| ---"):
                rows.append(tuple(cell.strip() for cell in line.strip("|").split("|")))
        elif rows:
            tables.append(tuple(rows))
            rows = []
    return tuple(tables)


def _normalized(section: str) -> str:
    return " ".join(section.split())


def _class_fields(path: Path, class_name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(path), filename=str(path))
    classes = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    assert len(classes) == 1
    return tuple(
        node.target.id
        for node in classes[0].body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    )


def _enum_members(path: Path, class_name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(path), filename=str(path))
    classes = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    assert len(classes) == 1
    return tuple(
        target.id
        for node in classes[0].body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    )


def test_scope_headings_starting_authority_and_zero_delta_are_exact() -> None:
    document = _read()
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == HEADINGS
    )

    scope = _section(document, "Answer And Static Scope")
    assert _tables(scope)[0][1:] == (
        ("Production changes", "`0`"),
        ("Public behavior changes", "`0`"),
        ("Public schema changes", "`0`"),
        ("Grammar/generated changes", "`0`"),
        ("AST/semantic/IR/SQL changes", "`0`"),
        ("CLI/JSON/Project Explain changes", "`0`"),
        ("Package/dependency/workflow changes", "`0`"),
        ("Golden/version changes", "`0`"),
        ("Slice 2 implementation", "`FORBIDDEN`"),
        ("Current version", "`0.1.0`"),
    )
    assert "Phase 62 extends the published Phase-61 Project IR" in scope
    assert "second Project compiler" in scope

    starting = _normalized(_section(document, "Starting Authority"))
    for evidence in (
        "7f78077d45bad378c1fb01561455a15ec95309b9",
        "398e68027e1259bd191d571af9df99436d2782fc",
        "34a9f48811101b0df66119db94277ff2fbfd9d23",
        "33359859544",
        "Complete Phase 61 Project IR",
        "attempt `1`",
        "Python 3.12 successful; Python 3.13 successful",
        "Phase 61 = COMPLETED",
        "Phase61 self-owned-open = 0",
        "Phase 62 = NEXT / NOT IMPLEMENTED",
        "154 passed",
    ):
        assert evidence in starting


def test_current_upstream_snapshots_and_all_dispositions_are_complete() -> None:
    document = _read()
    snapshot = _tables(_section(document, "Audit Method And Current Source Snapshots"))[
        0
    ][1:]
    assert {row[0]: row[2].strip("`") for row in snapshot} == UPSTREAM_HEADS
    assert all("https://" in row[3] and row[2].strip("`") in row[3] for row in snapshot)

    dispositions = _tables(
        _section(document, "Mature Source, Specification, And Research Dispositions")
    )[0][1:]
    assert {row[3] for row in dispositions} == {
        "`ADOPT`",
        "`ADAPT`",
        "`REJECT`",
        "`LATER_OWNER`",
    }
    assert {
        "dbt / MetricFlow",
        "MetricFlow",
        "SQLAlchemy",
        "ent",
        "DataFusion",
        "Cube",
        "PostgreSQL",
        "DuckDB",
        "Hasura",
        "Beam",
        "Malloy",
        "Apache Calcite",
        "Substrait",
    }.issubset({row[0] for row in dispositions})
    assert all(len(row) == 4 and all(row) for row in dispositions)

    normalized = _normalized(
        _section(document, "Mature Source, Specification, And Research Dispositions")
    )
    for evidence in (
        "local_remote_pairs",
        "OuterJoinSimplification",
        "NULL-filtered",
        "NULL-required",
        "outer-to-inner/left/right/anti rewrites",
        "A Formalization of SQL with Nulls",
        "VeriEQL",
        "SQLSolver",
        "Factorized Databases",
        "Free Join",
        "Predicate Transfer",
        "Robust Predicate Transfer",
        "RPT+",
        "DBSP",
        "hidden shortest-path winner",
        "runtime observations as semantic proof",
    ):
        assert evidence in normalized


def test_live_relationship_baseline_matches_current_source() -> None:
    grammar = _read(GRAMMAR)
    relationship_body = grammar[
        grammar.index("\nrelationshipDefinition\n") : grammar.index(
            "\nmoduleStatement\n"
        )
    ]
    assert (
        "relationshipEndpoint NEWLINE* relationshipEndpoint NEWLINE* relationshipMatchClause?"
        in relationship_body
    )
    assert _class_fields(AST_NODES, "RelationshipEndpoint") == (
        "local_name",
        "relation_name",
    )
    assert _class_fields(AST_NODES, "RelationshipMetadata") == (
        "name",
        "endpoints",
        "base_match",
    )
    assert _class_fields(AST_NODES, "RelationshipMatchClause") == ("expression",)
    assert _class_fields(SEMANTIC_MODEL, "RelationshipSemanticEndpointInfo") == (
        "local_name",
        "relation_name",
        "relation",
    )
    assert _class_fields(SEMANTIC_MODEL, "RelationshipSemanticInfo") == (
        "name",
        "endpoints",
    )

    builder = _read(AST_BUILDER)
    assert "assert len(endpoints) == 2" in builder
    assert "endpoints=(endpoints[0], endpoints[1])" in builder
    assert "base_match=" in builder
    assert "visitRelationshipMatchClause" in builder

    semantic = _read(RELATIONSHIP_SEMANTICS)
    for evidence in (
        "for relationship in script.relationships",
        "PIE-S2601",
        "PIE-S2602",
        "PIE-S2603",
        "relation_symbols.get(endpoint.relation_name)",
        "RelationshipSemanticInfo",
        "endpoints=(endpoints[0], endpoints[1])",
    ):
        assert evidence in semantic
    assert "check_relationship_metadata(" in _read(SEMANTIC_ANALYZER)

    assert _class_fields(IR_MODEL, "ScriptIR") == ("definitions",)
    ir_builder = _read(IR_BUILDER)
    assert "for definition in script.definitions" in ir_builder
    assert "script.relationships" not in ir_builder

    project_fields = set(_class_fields(PROJECT_MODEL, "ProjectSemanticModel"))
    assert {"catalog", "source_shape_resolutions", "relation_row_schemas"} <= (
        project_fields
    )
    assert not {"relationships", "relationship_resolutions", "joins"} & project_fields
    assert "RelationshipMetadata" not in _read(MODULE_CATALOG)

    baseline = _normalized(_section(_read(), "Live Pietto Relationship Baseline"))
    for evidence in (
        "Current `relationship` support is not parse-only",
        "existing public RelationshipSemanticInfo != new private Phase-62 Project relationship authority",
        "Self-relationships are already legal",
        "Project/module relationship occurrence identity",
        "field match correspondences",
        "relationship paths",
        "logical JOIN occurrences",
        "multi-fact alignment",
    ):
        assert evidence in baseline


def test_live_unique_baseline_is_evidence_readiness_not_key_authority() -> None:
    assert _class_fields(AST_NODES, "UniqueDef") == ("name", "field_names")
    assert _class_fields(IR_MODEL, "ShapeUniqueIR") == ("name", "fields", "span")

    grammar = _read(GRAMMAR)
    assert "UNIQUE identifier ON identifier (COMMA identifier)* NEWLINE" in grammar
    shape_semantics = _read(SHAPE_SEMANTICS)
    for evidence in (
        "isinstance(item, (UniqueDef, IndexDef))",
        "PIE-S2501",
        "PIE-S2502",
        "PIE-S2503",
        "Unknown target field",
        "Duplicate target field",
    ):
        assert evidence in shape_semantics
    assert "return ShapeUniqueIR(" in _read(IR_BUILDER)

    project_fields = set(_class_fields(PROJECT_MODEL, "ProjectSemanticModel"))
    assert not {"uniques", "keys", "functional_dependencies", "grain"} & project_fields
    fact_fields = set(
        _class_fields(MODULE_SEMANTIC_FACTS, "ProjectModuleRelationSemanticFacts")
    )
    assert not {"uniques", "keys", "functional_dependencies", "grain"} & fact_fields
    row_keys = _read(PROJECT_ROW_KEYS)
    for evidence in (
        "class ProjectUniqueDeclarationIdentity",
        "class ProjectRowUniquenessEvidenceIdentity",
        "class ProjectRowUniquenessEvidence",
        "class ProjectCandidateKeyFact",
        "ProjectUniqueNullPolicy.NULLS_DISTINCT",
        "ProjectRowUniquenessStrength.STRICT",
        "ProjectRowUniquenessStrength.LAX",
        "check_shape_structures",
        "ProjectExactRowOutputConstraintScope",
    ):
        assert evidence in row_keys
    assert "__all__: tuple[str, ...] = ()" in row_keys

    baseline = _normalized(_section(_read(), "Live Pietto UNIQUE Baseline"))
    assert "existing authored UNIQUE = potential semantic evidence premise" in baseline
    for non_authority in (
        "candidate-key authority",
        "value-FD authority",
        "grain authority",
        "relationship-cardinality authority",
    ):
        assert non_authority in baseline
    assert "No new UNIQUE syntax or semantics is implemented" in baseline


def test_live_slice5_value_fd_foundation_preserves_separate_private_domains() -> None:
    source = _read(PROJECT_VALUE_FDS)
    for evidence in (
        "class ProjectValueFDFieldUniverse",
        "class ProjectValueFDIdentity",
        "class ProjectValueFDFact",
        "class ProjectValueFDIndex",
        "class ProjectValueFDBasisSet",
        "class ProjectValueFDDeterminationStatus",
        "def build_project_value_fds",
        "def strict_value_fd_closure",
        "def strictly_determines",
        "ProjectCandidateKeyFact",
        "ProjectRowUniquenessStrength.STRICT",
        "ProjectRowUniquenessStrength.LAX",
        "ProjectConstraintEvidenceOrigin.DERIVED_THEOREM",
        "ProjectConstraintEvidenceTrust.TRUSTED",
        "ProjectConstraintEnforcementPosture.MODEL_CONTRACT",
        "ProjectExactRowOutputConstraintScope",
        "MappingProxyType",
        "bit_count",
        "deque",
    ):
        assert evidence in source
    assert "__all__: tuple[str, ...] = ()" in source
    assert "build_project_relationship_conditions" not in source
    assert "ProjectRelationshipEqualityCorrespondence" not in source
    assert "ProjectIR" not in source
    assert "grain" not in source.lower()
    assert "value_fds" not in set(_class_fields(PROJECT_MODEL, "ProjectSemanticResult"))


def test_live_slice6_grain_foundation_preserves_factor_and_operator_boundaries() -> (
    None
):
    source = _read(PROJECT_GRAIN)
    for evidence in (
        "class ProjectGrainBasisState",
        "class ProjectSourceGrainFactorIdentity",
        "class ProjectGroupedGrainFactorIdentity",
        "class ProjectGrainDependencyFact",
        "class ProjectGrainBasis",
        "class ProjectGrainOriginSet",
        "def build_project_grain_origins",
        "def grain_dependency_closure",
        "ProjectIRAggregateEvaluationContext",
        "ProjectValueFDBasisSet",
        "NOT_CONSTRUCTIBLE_BEFORE_LOGICAL_JOIN",
    ):
        assert evidence in source
    assert "__all__: tuple[str, ...] = ()" in source
    assert "ProjectValueFDFact" not in source
    assert "ProjectCompiledValueFDRule" not in source
    assert "build_project_relationship" not in source
    assert "ProjectIRProvidedLocalGrainEvidence" not in source
    assert "grain" not in set(_class_fields(PROJECT_MODEL, "ProjectSemanticResult"))


def test_live_slice7_relational_properties_remain_private_and_post_verified() -> None:
    source = _read(PROJECT_IR_RELATIONAL_PROPERTIES)
    for evidence in (
        "class ProjectIRRelationalPropertyStage",
        "class ProjectIRProvidedIntrinsicGrain",
        "class ProjectIROutputCandidateKey",
        "class ProjectIROutputValueFD",
        "ProjectIRAnalysisBundle",
        "topological_order",
        "build_project_ir_relational_property_stage",
    ):
        assert evidence in source
    assert "__all__: tuple[str, ...] = ()" in source


def test_live_slice8_match_guarantees_preserve_key_coverage_and_join_boundaries() -> (
    None
):
    source = _read(PROJECT_RELATIONSHIP_MATCH_GUARANTEES)
    for evidence in (
        "class ProjectRelationshipDirectionIdentity",
        "class ProjectReferentialCoverageEvidence",
        "class ProjectDirectionalRelationshipMatchGuarantee",
        "MATCH_SIMPLE",
        "MATCH_FULL",
        "UNBOUNDED_BY_ONE",
        "build_project_relationship_match_guarantees",
    ):
        assert evidence in source
    assert "__all__: tuple[str, ...] = ()" in source
    assert "MATCH_PARTIAL" not in source


def test_phase61_inheritance_and_identity_ownership_laws_are_exact() -> None:
    inherited = _normalized(_section(_read(), "Phase 61 Inherited Readiness"))
    for evidence in (
        "exact module/relation/field occurrence identity",
        "Project semantic-fact occurrence identity",
        "plan-node refs",
        "output-value refs",
        "input-slot refs",
        "use refs",
        "BAG/multiset semantics",
        "INPUT / BASE_RESULT / FINAL stage rows",
        "provided/required property domains",
        "producer-output -> use -> consumer-slot topology",
        "aggregate/window evaluation contexts",
        "independent verifier",
        "winner-free typed queries",
        "real authored multi-module E2E",
        "Python 3.12/3.13 differential assurance",
        "Phase 62 extends Phase-61 Project IR",
        "Phase 62 builds a second Project compiler",
    ):
        assert evidence in inherited

    identity = _normalized(
        _section(_read(), "Fundamental Identity, Ownership, And Visibility Laws")
    )
    for evidence in (
        "relationship declaration != relationship endpoint occurrence != directed relationship traversal occurrence != relationship path occurrence != logical JOIN occurrence",
        "module declaration occurrence != field occurrence != Project semantic-fact occurrence != ProjectIR plan node != ProjectIR output value != ProjectIR use != ProjectIR input slot != grain factor != future runtime row identity != persistent cache identity",
        "Same endpoints do not imply the same relationship",
        "Self-relationships are legal",
        "Order.order_date -> Date",
        "Order.ship_date -> Date",
        "Relationship-graph cycles may be legal",
        "module-local relationship != reusable/importable relationship asset",
        "Public relationship/key/FD/grain/JOIN exposure remains Phase 70",
    ):
        assert evidence in identity


def test_conditions_paths_and_formal_bag_null_laws_are_exact() -> None:
    conditions = _normalized(_section(_read(), "Relationship Conditions And Paths"))
    for evidence in (
        "ordered, non-empty conjunction",
        "exact endpoint field equality correspondences",
        "There is no same-name inference",
        "relationship base match condition != JOIN-local ON refinement != post-JOIN ROW_FILTER / WHERE",
        "Arbitrary residual Boolean predicates never contribute",
        "exact relationship occurrence",
        "exact direction",
        "exact step order",
        "exact traversal occurrence",
        "More than one direct candidate yields `AMBIGUOUS`",
        "No analysis enumerates all graph walks",
    ):
        assert evidence in conditions

    bag = _normalized(_section(_read(), "Formal BAG And NULL Reference Semantics"))
    for evidence in (
        "R: Tuple -> non-negative multiplicity",
        "predicate(l, r) = TRUE",
        "predicate(l, r) = FALSE or UNKNOWN",
        "R(l) * S(r) * matches(l, r)",
        "J_left(null_extend(l)) += R(l)",
        "FALSE and UNKNOWN never match",
        "LEFT JOIN != matched/unmatched branch expansion in canonical IR",
        "bounded oracle != complete theorem prover != runtime evaluator != production engine != SMT proof certificate",
    ):
        assert evidence in bag


def test_unique_evidence_typed_proof_and_cardinality_laws_are_exact() -> None:
    unique = _normalized(
        _section(_read(), "UNIQUE Null Policy And Constraint Evidence")
    )
    for evidence in (
        "NULLS_DISTINCT",
        "NULLS_NOT_DISTINCT",
        "strict key != lax key",
        "strict FD != lax FD",
        "nullable UNIQUE != automatically unusable",
        "Unrestricted transitivity is forbidden for lax dependencies",
        "exact subject row output",
        "semantic scope",
        "trust posture",
        "null semantics",
        "enforcement posture",
        "AUTHORED_CONTRACT",
        "CATALOG_CONSTRAINT",
        "DERIVED_THEOREM",
        "RUNTIME_OBSERVATION",
        "UNVERIFIED_HINT",
        "trusted authored contract != database-verified physical constraint",
        "UNCONDITIONAL_ON_EXACT_ROW_OUTPUT",
        "UNDER_MATCH_CONTEXT",
    ):
        assert evidence in unique

    typed = _normalized(_section(_read(), "Typed Keys, FDs, Grain, And Coverage"))
    for evidence in (
        "Value functional dependency: FieldSet -> FieldSet",
        "Row uniqueness / key",
        "Grain dependency: GrainFactorSet -> GrainFactorSet",
        "Directional match guarantee",
        "Value FD != Row uniqueness != Candidate key != Intrinsic grain",
        "complete field-subset power set is never enumerated",
        "direct evidence = authority closure = derived analysis",
        "ReferentialCoverageEvidence",
        "MATCH SIMPLE",
        "MATCH FULL",
        "foreign-key-like coverage != value FD",
    ):
        assert evidence in typed

    cardinality = _normalized(
        _section(_read(), "Directional Match Guarantees And Runtime Enforcement")
    )
    for evidence in (
        "ZERO_ALLOWED",
        "AT_LEAST_ONE",
        "AT_MOST_ZERO",
        "AT_MOST_ONE",
        "UNBOUNDED_BY_ONE",
        "no proven at-most-one guarantee",
        "proof that two or more matches exist",
        "cardinality guarantee != authored display label != row-count estimate != observed multiplicity != runtime single-match enforcement",
        "ordinary LEFT JOIN with static at-most-one proof is not a single-match JOIN",
        "`INNER` and `LEFT` only",
    ):
        assert evidence in cardinality


def test_join_grain_fanout_multifact_and_algorithm_boundaries_are_exact() -> None:
    join = _normalized(
        _section(_read(), "Canonical JOIN Region, Nulling, And Ordering")
    )
    for evidence in (
        "binary input/JOIN region DAG + existing ordered unary tail",
        "two input slots",
        "two exact producer uses",
        "one output relation-row occurrence",
        "Authored JOIN order is canonical",
        "one canonical binary JOIN occurrence",
        "side-specific nulling provenance",
        "outer-join legality barrier",
        "definitely not TRUE",
        "Unknown functions/predicates stay unknown",
        "join ordering preservation = unknown unless exact later authority proves it",
    ):
        assert evidence in join

    assert _enum_members(PROJECT_IR_OPERATORS, "ProjectIRLogicalOperatorKind") == (
        "RELATION_INPUT",
        "ROW_FILTER",
        "GROUP_AGGREGATE",
        "RESULT_FILTER",
        "WINDOW_EVALUATION",
        "FINAL_PROJECTION",
        "RELATION_ORDERING",
        "LIMIT",
    )

    grain = _normalized(
        _section(_read(), "Intrinsic Grain And Compact Closure Architecture")
    )
    for evidence in (
        "intrinsic row grain != visible key fields",
        "Self-joins and role-playing uses produce distinct factors",
        "GLOBAL",
        "FACTORIZED",
        "UNKNOWN",
        "CONFLICT",
        "shared basis != shared property occurrence",
        "empty key / max-one-row != GlobalGrain",
        "GrainFactorSet -> GrainFactorSet",
        "LEFT_FINER",
        "RIGHT_FINER",
        "INCOMPARABLE",
        "AMBIGUOUS",
        "common_grain(...) -> one hidden winner",
        "bit position != semantic identity",
        "atom -> rules containing atom in LHS",
        "JOIN-local equality class != field identity",
    ):
        assert evidence in grain

    fanout = _normalized(
        _section(_read(), "Fanout, Fact Locality, Multi-Fact, And Join Shape")
    )
    for evidence in (
        "PRESERVES_SOURCE_MULTIPLICITY",
        "MAY_MULTIPLY",
        "relationship cardinality != fanout result",
        "fact occurrence != relation declaration",
        "EXACTLY_ALIGNED",
        "REAGGREGATION_REQUIRED",
        "FANOUT_RISK",
        "CROSS_FACT_MULTIPLICATION",
        "Customer -> Orders = many",
        "Customer -> Returns = many",
        "ACYCLIC",
        "CYCLIC",
        "NOT_APPLICABLE",
        "Join shape is not a physical plan",
    ):
        assert evidence in fanout

    rejected = _normalized(
        _section(_read(), "Rejected Algorithms And Assurance Boundary")
    )
    for evidence in (
        "matched/unmatched DNF expansion",
        "per-stage duplicate row-axis graph",
        "one untyped universal implication engine",
        "all candidate-key power-set enumeration",
        "all relationship-path enumeration",
        "shortest-path automatic winner",
        "name-based join inference",
        "ambient current-project/current-relation registry",
        "global mutable interning",
        "hash-derived semantic identity",
        "bytes-derived identity",
        "physical JOIN strategy in canonical semantic identity",
    ):
        assert evidence in rejected


def test_route_later_owners_exit_gate_and_static_delta_are_exact() -> None:
    route = _tables(_section(_read(), "Exact 16-Slice Route"))[0][1:]
    assert tuple((row[0], row[1]) for row in route) == ROUTE
    assert tuple(int(row[0]) for row in route) == tuple(range(1, 17))
    assert len({row[1] for row in route}) == 16
    assert "ARCHITECTURE_DECISION_REQUIRED" in _section(_read(), "Exact 16-Slice Route")

    later = _tables(_section(_read(), "Exact Later-Owner Ledger"))[0][1:]
    assert tuple(row[0] for row in later) == (
        "Phase 63",
        "Phase 64",
        "Phase 65",
        "Phase 66",
        "Phase 67",
        "Phase 68",
        "Phase 69",
        "Phase 70",
        "Dedicated recursion owner",
        "Dedicated persistent analysis/cache owner",
        "Dedicated incremental/differential owner",
        "Dedicated formal rewrite-certification owner",
        "Dedicated data-quality/discovery owner",
        "Dedicated general-constraint owner",
    )
    assert all(row[1] for row in later)
    later_by_owner = {row[0]: row[1] for row in later}
    for evidence in (
        "bitset",
        "FD-closure",
        "grain-analysis",
        "profiling-driven",
    ):
        assert evidence in later_by_owner["Phase 68"]
    for evidence in (
        "Catalog-backed PK/UNIQUE/FK evidence",
        "catalog-vs-authored conflict validation",
        "runtime statistics",
        "cardinality/selectivity estimates",
        "optimizer memo",
        "DPccp",
        "DPhyp",
        "outer-join conflict/reordering rules",
        "cutoff and heuristic fallback",
        "factorized physical execution",
        "robust predicate transfer",
        "semijoin reduction",
        "Yannakakis",
        "Free Join / WCOJ",
        "AGM/worst-case bounds",
        "hash/merge/nested-loop strategies",
        "backend-specific join capabilities",
    ):
        assert evidence in later_by_owner["Phase 69"]
    assert "ProjectIR occurrence identity != runtime/delta row identity" in (
        _normalized(_section(_read(), "Exact Later-Owner Ledger"))
    )

    exit_section = _normalized(
        _section(_read(), "Phase 62 Exit Criteria And Phase 63 Handoff")
    )
    for evidence in (
        "relationship declaration -> exact endpoint resolution -> exact field correspondences -> UNIQUE/key/FD evidence -> intrinsic grain basis -> referential coverage -> directional match guarantees -> explicit relationship paths -> authored INNER/LEFT JOIN -> canonical Project IR binary JOIN region",
        "fanout analysis",
        "multi-fact alignment classification",
        "Python 3.12/3.13 differential assurance",
        "no hidden relationship/path winner",
        "no BAG->SET collapse",
        "no silent fanout",
        "no silent reaggregation",
        "Phase62 self-owned-open = 0",
    ):
        assert evidence in exit_section

    readers = _normalized(
        _section(_read(), "Reader Closure, Changed-Path Lock, And Zero Delta")
    )
    assert "A2/M7/D0" in readers
    assert "sole direct reader" in readers
    assert "A tenth changed path is `READER_CLOSURE_DRIFT`" in readers
    assert "production 0" in readers
    assert "grammar/generated 0" in readers
    assert "AST/semantics/IR 0" in readers
    assert "workflow 0" in readers
    assert "version 0.1.0" in readers

    gate = _normalized(_section(_read(), "Review, Gate, Publication, And Next Owner"))
    for evidence in (
        "initial review allowed and consumed one same-root, same-Slice, frozen-allowlist repair batch",
        "STALE_PHASE61_COMPLETION_TEST_ENCODES_HISTORICAL_PHASE62_UNSTARTED_STATE AS_A_PERMANENT_CURRENT_REPOSITORY_ABSENCE_ASSERTION",
        "repair batches allowed: 2",
        "cumulative terminal accounting: 2/2",
        "No further repair or path is authorized",
        "Fresh complete rereview",
        "ARCHITECTURE_DECISION_REQUIRED",
        "REVIEW_RECURRENCE",
        "UV_PYTHON=3.13 uv run python scripts/validate.py --timings",
        "one ordinary non-amend commit",
        "one fast-forward push",
        "without dispatch, rerun, or cancellation",
        "Add Phase 62 relationship and grain route lock",
        "PASS — PHASE62_SLICE1_RELATIONSHIP_JOIN_KEYS_FD_GRAIN_FANOUT_MULTIFACT_ARCHITECTURE_SOURCE_AUDIT_ROUTE_LOCK_END_TO_END",
        "Phase 62 Slice 2 — Relationship Declaration Identity, Endpoint Roles, Module-Local Resolution, And Construction States",
        "Slice 2 is not implemented or authorized",
    ):
        assert evidence in gate

    assert not any(
        (REPO_ROOT / path).exists()
        for path in (
            "src/pietto/_project/project_join.py",
            "src/pietto/_project/project_keys.py",
            "src/pietto/_project/project_functional_dependencies.py",
            "src/pietto/_project/project_fanout.py",
            "src/pietto/_project/project_multifact.py",
        )
    )
