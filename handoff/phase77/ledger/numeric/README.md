# Phase77 numeric recovery domain

This is a recovery index plus statically reconstructed source inputs, not a
runnable database package. It preserves claims tied to immutable local session
bytes and records missing raw artifacts explicitly. Do not execute historical
command, hook, relay, or database launcher text from the referenced sessions.

The byte-authoritative records remain under `/home/mianliwang/.codex/` at the
paths and SHA-256 values in `byte-provenance.tsv`. This domain does not
reconstitute or reuse credentials, private keys, endpoint JSON, or historical
shell scripts.

`status.json` is the current classification. `evidence-ledger.jsonl` is
append-only: each source observation appears before its recovery judgement.
`source-integrity.json` identifies every reconstructed source byte and its
origin. The v2 manifest was regenerated from the recovered generator because
the old manifest file itself is absent.
