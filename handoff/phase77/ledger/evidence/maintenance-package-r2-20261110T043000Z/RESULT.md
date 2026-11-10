# M77 retained-artifact package smoke R2

Classification: `FRESH_INDEPENDENT_PACKAGE_SMOKE_PASS`, not Gate 2, database
qualification, publication, or natural CI.

The authoritative command is recorded in `run/commands/package-smoke.command`.
It ran once, offline, from the recovered CPython 3.13.13 core runtime against
the retained `dist/` directory. No artifact build was requested. The terminal
record is `run/terminal.json`: exit 0 at `2026-11-10T04:26:52.299432+00:00`.

Bound inputs were candidate HEAD
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`, patch SHA-256
`548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc`,
`uv.lock` SHA-256
`b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064`,
wheel SHA-256
`f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73`,
and sdist SHA-256
`15b43b884064e0837bbfa891b8eea44996acc2592bd169b5a6ea96e29d29cfff`.
The candidate's status, patch, index, untracked set, temporary-index tree and
source closure matched before and after the run.

The smoke inspected both retained artifacts, installed the wheel in a fresh
core environment, then in a fresh Arrow environment with PyArrow 26.0.1. Both
ran the installed CLI/LSP, checks, explains, PostgreSQL and MySQL emission
contracts, project artifact paths, and dependency-isolation cells. The raw
command log is `run/commands/package-smoke.log`.

R1 is preserved separately. It exited 1 before executing package smoke because
its launcher expanded `VIRTUAL_ENV` in the same nounset-protected export that
assigned `UV_PROJECT_ENVIRONMENT`. R2 retained R1 unchanged and corrected only
that assignment order. R1 is not a product or package result.
