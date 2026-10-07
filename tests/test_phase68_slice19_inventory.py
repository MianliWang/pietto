"""S19 required matrix: an independent derivation from the lower-level case
owners, cross-checked against the producers' manifests, with every inventory
damage rejected by its designated law. Pure; no database, Arrow or network."""

import pytest

import _pietto_phase68_slice10_probe as s10
import _pietto_phase68_slice14_probe as s14
import _pietto_phase68_slice19_check as check


@pytest.mark.parametrize(
    "target,totals",
    [
        ("postgres", (166, 0, 62, 1328, 496, 0)),
        ("mysql", (164, 5, 62, 636, 240, 5)),
    ],
)
def test_required_matrix_equals_the_producer_owners(target, totals):
    found = check.cross_check(
        target, s10.native_manifest(target), s14.r2_families(target)
    )
    assert (
        found["declared"],
        found["excluded"],
        found["r2"],
        found["cells"],
        found["r2_cells"],
        found["exclusions"],
    ) == totals
    cells, excluded = check.required(target)
    assert {c[1] for c in cells} == set(check.ROUTES[target])
    assert {(c[6], c[5]) for c in cells} == set(check.CELLS)
    assert all(k[0] == target for k in excluded)


def test_a_shortened_producer_manifest_cannot_pass():
    manifest = s10.native_manifest("postgres")
    with pytest.raises(check.CheckError, match="INVENTORY_MANIFEST"):
        check.cross_check("postgres", manifest[:-1], s14.r2_families("postgres"))
    r2 = s14.r2_families("postgres")
    with pytest.raises(check.CheckError, match="INVENTORY_R2"):
        check.cross_check("postgres", manifest, r2[1:])
    # A target exclusion applied to PostgreSQL is foreign to its contract.
    shifted = [dict(m) for m in manifest]
    shifted[0]["excluded"] = True
    with pytest.raises(check.CheckError, match="INVENTORY_MANIFEST"):
        check.cross_check("postgres", shifted, r2)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_inventory_damages_are_rejected_by_their_laws(target):
    records = check.as_records(target)
    assert check.check_inventory(target, records)["cells"] == len(
        check.required(target)[0]
    )
    assert check.inventory_damages(target, records) == {
        "omitted": "INVENTORY_OMITTED",
        "duplicated": "INVENTORY_DUPLICATE",
        "foreign": "INVENTORY_FOREIGN",
        "relabeled": "INVENTORY_FOREIGN",
        "recast": "INVENTORY_RECAST",
    }


def test_exclusions_keep_their_original_owner():
    records = check.as_records("mysql")
    dropped = [r for r in records if "excluded" in r]
    assert sorted((tuple(r["excluded"][1:]) for r in dropped), key=repr) == sorted(
        check.EXCLUSIONS["mysql"], key=repr
    )
    damaged = [dict(r) for r in records]
    index = next(i for i, r in enumerate(damaged) if "excluded" in r)
    damaged.pop(index)
    with pytest.raises(check.CheckError, match="INVENTORY_EXCLUSION"):
        check.check_inventory("mysql", damaged)
    # An exclusion is the original owner's own refusal, never another reason
    # (missing tooling, a budget, a new failure) under the same name.
    for field, value in (("owner", "budget"), ("observed", "TimeoutError")):
        relabeled = [dict(r) for r in records]
        guarded = next(
            i
            for i, r in enumerate(relabeled)
            if "excluded" in r and r["excluded"][1] == "guarded"
        )
        relabeled[guarded][field] = value
        with pytest.raises(check.CheckError, match="INVENTORY_EXCLUSION"):
            check.check_inventory("mysql", relabeled)


def test_evidence_classes_need_their_backing_observation():
    assert check.check_evidence(
        {"evidence": "SIGKILL", "returncode": -9, "reaped": True}
    )
    assert check.check_evidence({"evidence": "REAL_COMPONENT"})
    for record in (
        {"evidence": "SIGKILL", "returncode": 0, "reaped": True},
        {"evidence": "NATIVE", "session": None, "route": "postgres_rows"},
        {"evidence": "MODEL", "returncode": -9},
        {"evidence": "POWER_LOSS"},
    ):
        with pytest.raises(check.CheckError, match="EVIDENCE_CLASS"):
            check.check_evidence(record)


def test_joint_model_explores_its_visible_bounds():
    assert check.joint_model(2) == check.joint_model(chunks=2)
    assert 0 < check.joint_model(1) < check.joint_model(2)
