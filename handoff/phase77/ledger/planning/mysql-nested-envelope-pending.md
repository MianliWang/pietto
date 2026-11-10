# MySQL nested transport seam — historical proposal

Status: `HISTORICAL_PROPOSAL_OWNER_DECISION_PENDING`.

MySQL Collect/Unnest remains refused. The recovered proposal explicitly keeps
three states distinct: an empty collection, one all-NULL child row, and an
outer-join absent container. It also requires preservation of child occurrence
identity, child-port order, multiplicity, authored ordering/tie law, parent
batch boundaries and LEFT-join placeholder semantics.

`JSON_ARRAYAGG` and `JSON_TABLE` are candidate primitives, not evidence. The
proposal requires a prewritten logical oracle and generated-SQL campaign before
admitting JSON behavior for Int64, Decimal scale, finite Float/signed zero,
Text, UUID, Date/Timestamp, child NULL, and expansion grain.

The conservative candidate is a private versioned wire containing explicit
container presence/count and typed source-ordered child sequences, validated
before Arrow allocation. Selecting that wire, selecting JSON encoding, changing
compiled records, and any compatibility mark are `OWNER_DECISION_PENDING`.
Nothing in this recovery selects them or authorizes a DB campaign.

The source patch is recoverable from `records/duckdb_seam.jsonl:707,713,719,725`.
