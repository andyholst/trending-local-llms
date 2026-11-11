# §6's role text is guarded by the BOUNDARY, not by a prose reader

**Issue:** [#508](https://github.com/andyholst/trending-local-llms/issues/508)
**Capability:** `architecture-role-boundary`

## Why

`architecture_check.described_scripts()` proves a §6 row EXISTS whose first cell
names the path; it cannot tell that the role text beside it still describes the
code. A row that exists but lies is worse than a missing row, because the check
now reports the file as described. The repo already draws this boundary
deliberately (`#182`: the guard "cannot read prose"), but the §6 ROLE column had
no plain statement of the boundary — so a reader could read each row as a
verified claim. This change states the boundary for the role text where the
rows are, instead of pretending to verify prose.

## What Changes

- **`ARCHITECTURE.md` §6** — a lead-in paragraph, before the table, stating
  plainly that the Role column is HUMAN review text: the guard proves only that
  a row exists naming the script (its FIRST cell), never that the role beside it
  still matches the code. Keeping a role true is a reviewer's job, and a role
  that stopped matching is a defect a human fixes — not a claim the machine made.
- **`ARCHITECTURE.md` "What the guard proves — and what it does not"** — the §6
  bullet now names the role column as first-cell-presence-only, so the contract
  at the top and the §6 lead-in cannot drift.
- **`scripts/architecture_check.py`** — `described_scripts()` docstring states
  the same boundary (reads the FIRST cell only; role text is not verified), so
  the guard's own words and the document's promise agree.
- **`tests/test_architecture.py`** — a new test locks both statements (the §6
  lead-in and the module docstring), so the boundary cannot rot back into a
  claim that the guard verifies role prose.

## Impact

Documentation + one docstring + one test. No change to what the guard FAILS on:
a script missing from §6 is still red (issue #506). This does not weaken any
check; it removes the false implication that the role text is machine-verified.

## Not covered (out of scope)

- Machine-verifying role prose (a `# arch-role:` header or `--help` first-line
  comparison). That is deliberately NOT done: it would contradict the
  documented `#182` boundary that the guard cannot read prose, and prose tags
  on 58 scripts would rot as fast as the rows do. The issue's "Done when" ORs
  the doc statement against the mechanical claim — this implements the former.
