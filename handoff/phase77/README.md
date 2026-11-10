# Phase77 machine handoff (not for main)

This directory moves the Phase77 working state from one development machine
to another. It is not product content and must never be merged into `main`.
Start with [ledger/HANDOFF-NEXT-MACHINE-zh.md](ledger/HANDOFF-NEXT-MACHINE-zh.md).

- `ledger/`: the recovery ledger subset (reports, reviews, decisions, small
  evidence logs and bindings). Private session records, raw native receipts,
  caches and virtual environments are excluded.
- `candidate-exports/`: each candidate as base `HEAD`, `tracked.patch` and
  untracked files; restore them with `ledger/restore-candidates.sh`.
