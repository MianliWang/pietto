"""Shared compiled-family fixture for execution-layer tests."""

from _pietto_execution_binding import proof_artifact


def retained_unmapped_source(directory, target, variant, monkeypatch):
    import _pietto_sql_emission as probe

    original = probe.join_witness

    def with_unselected_source(_target, body, **options):
        selected, unused = body.split("query unused:", 1)
        relation = {
            "key": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n",
            "limit": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n    limit 1\n",
            "global": "table unused_ranked:\n    from unused_rows\n    select:\n        id = count()\n",
            "grouped": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n    limit 1\n",
            "window": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n    limit 1\n",
            "set": "table unused_base:\n    from unused_rows\n    select:\n        id\ntable unused_union:\n    union all:\n        from unused_base\n        from unused_base\ntable unused_ranked:\n    from unused_union\n    select:\n        id\n    limit 1\n",
            "ordered": "table unused_ranked:\n    from unused_rows\n    select distinct:\n        id\n    order by:\n        id\n    limit 1\n",
        }[variant]
        unused = unused.replace("join ranked as", "join unused_ranked as")
        if variant == "grouped":
            unused = unused.replace(
                "    select:\n        value = lhs.id\n",
                "    group by:\n        lhs.id\n    select:\n        value = lhs.id\n        total = count()\n",
            )
        if variant == "window":
            unused += "    qualify:\n        row_number() window:\n            order by:\n                lhs.id\n        <= 0\n"
        body = (
            f'source unused_rows: Row is {target}.table("unused_rows")\n'
            + relation
            + selected
            + "query unused:"
            + unused
        )
        if variant == "key":
            body = body.replace(
                "source unused_rows: Row", "source unused_rows: UnusedRow"
            )
        fixture = original(target, body, **options)
        if variant == "key":
            fixture["source"] = fixture["source"].replace(
                "source lhs:",
                "shape UnusedRow:\n    id: Int not null\n    key: Int nullable\n    unique unused_id on id\nsource lhs:",
                1,
            )
        return fixture

    monkeypatch.setattr(probe, "join_witness", with_unselected_source)
    return proof_artifact(directory, retained=True)
