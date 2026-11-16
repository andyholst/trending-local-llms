# Proposal: land-invalid-change-repair-owed-rows

Issue: #1087 (the §6q keeper-registry text and the §8 guard row #962 owed and could not write)

## Why

PR #1086 landed the third `openspec-check` repairer: an ACTIVE change that shipped INCOMPLETE
(a `proposal.md` with no spec and no tasks) reds the merge gate while `index-repair` correctly
answers `DRIFT=none` and names no repairer (measured run 43610043055). The code is on `master` —
`scripts/openspec_invalid_change_repair.py`, `make openspec-invalid-change-check` /
`openspec-invalid-change-repair`, and qa-validate's `invalid-change-repair` job — but the RULEBOOK
is not: `make owed-rows-check` measures both rows OUTSTANDING (`§2 needle='invalid-change-repair'
OUTSTANDING`, `§8 needle='tests/test_openspec_invalid_change_repair.py' OUTSTANDING`). A reader of
§6q still sees only two repairers for the gate, and §8 has no row for the new guard, so the next
agent re-derives the shape from git history instead of the rulebook. `AGENTS.md` is protected in a
headless leg (rule 3c), so the rows were DECLARED as owed instead of smuggled in — the shape
#476/#310/#391/#400 already established. This attended run lands them from the ledger.

## What Changes

- **`AGENTS.md` §2 (append to rule 6q's architecture-repair paragraph)**: the landed row text as
  written on #1087 — the THIRD shape of red (issue #962), the `invalid-change-repair` job, its
  `DRIFT=none|index-drift|invalid-change` verdict and `REPAIR=none|archived` half, the keeper-PR
  shape (`ci/openspec-invalid-change-repair-<UTC>`, archive-move-only, no closing keyword), the
  no-fabrication half (rule 2), and the registry naming all three repairers.
- **`AGENTS.md` §8**: the landed guard row naming `tests/test_openspec_invalid_change_repair.py`,
  `scripts/openspec_invalid_change_repair.py` and both Makefile targets, as written on #1087.
- **`tests/test_agents_rows.py`**: the landed rows are PINNED, not promised — a new check proves
  §6q carries the shape/target/verdict/registry phrases, §8 carries the guard row, and the modules
  the row names exist.

## Impact

- Affected specs: `rulebook-invalid-change-repair` (new capability)
- Affected code: `AGENTS.md` (protected; review-required per rule 3c), `tests/test_agents_rows.py`
- Not covered: no behaviour change to the repair seam itself (it shipped in #962/PR #1086); the
  §6s auto-merge-rebase row is its own issue (#1088) and its own change.
