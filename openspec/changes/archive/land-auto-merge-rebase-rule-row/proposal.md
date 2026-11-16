# Proposal: land-auto-merge-rebase-rule-row

Issue: #1088 (the §2/§8 rows #1049 owed and could not write)
PR: #1107

## Why

PR #1085 landed auto-merge's pre-squash rebase gate on `master`: qa-validate's
`Rebase a behind-and-clean bot branch` step runs `make auto-merge-rebase`
(`scripts/auto_merge_rebase.py`) before `Merge the green PR`, and the §6s sweep rebaser now
regenerates `OPENSPEC.md` on every rebased tree (measured root cause: PR #1071 — qa-validate
squashed a 3-commits-behind branch head whose stale index red-ed the push-to-master
`openspec-index-check`, while the next PR red-d the pre-merge gate). The code shipped, but a
headless leg cannot write the protected rulebook (rule 3c), so the rows were DECLARED owed on
#1088 and `make owed-rows-check` measured both OUTSTANDING (`§2 needle='auto-merge-rebase'`,
`§8 needle='tests/test_auto_merge_rebase.py'`). The rulebook still described auto-merge as a
bare "squash once checks are green" and §8 had no row for the new gate. This attended run lands
them from the ledger.

## What Changes

- **`AGENTS.md` §2 (rule 6e)**: after the squash-merge sentence — `make auto-merge-rebase` is
  auto-merge's pre-squash gate: behind+clean+bot-owned → rebase onto the fetched base and
  regenerate `OPENSPEC.md` on the rebased tree; `rebased=true` skips the squash so the merge lands
  at the validated head; human-owned/conflicting stays report-only (the §6s partition).
- **`AGENTS.md` §6s**: the sweep rebaser bullet now names the OPENSPEC.md regeneration on the
  rebased tree (issue #1088).
- **`AGENTS.md` §8**: the landed guard row for `tests/test_auto_merge_rebase.py` + the qa-validate
  step + the Makefile target, as written on #1088.
- **`tests/test_agents_rows.py`**: `test_the_auto_merge_rebase_row_is_written` pins all three
  rulebook pieces and that the named modules exist.

## Impact

- Affected specs: `rulebook-auto-merge-rebase` (new capability)
- Affected code: `AGENTS.md` (protected; review-required per rule 3c), `tests/test_agents_rows.py`
- Not covered: no change to the gate seam itself (shipped in #1049/PR #1085); the §6q/§8
  invalid-change-repair rows are their own issue (#1087) and landed in PR #1106.
