# Proposal: refusals-ledger-landing-declaration

**Issue:** [#1155](https://github.com/andyholst/trending-local-llms/issues/1155) — CI-only
PR: #1157
PRs dirty the refusals ledger. Capability: `data-refusal-ledger`.

## Why

`data/refusals.json` is DATA, and rule 3b lets it grow only on a real observation. Issue
#1148 made each finding land once (repeats raise `seen_count`), but it left the bigger
question unanswered: WHICH pass is allowed to write the file at all. The ingest refusal
seams write it from every pass over the tree, so a branch that touched no data grew it
anyway. Measured on the `tech-debt-agent-profile-provision-1142` worktree (issue #1155's own
evidence): after running the suite and validators for a fleet-profile provisioning change,
`git status --short` printed `M data/refusals.json` and `git diff` showed `seen_count` raised
to 2 with `last_seen_utc` stamped on three findings the refresh delivery had already recorded
(`2026-11-19T21:25:34Z`, `2026-11-19T21:31:37Z`) — nothing to do with provisioning fleet
profiles. It was discarded with `git checkout -- data/refusals.json` before the branch was
pushed, which is why PR #1153's diff carries no `data/` row at all: the churn is real, it is
just manually removed today instead of being prevented. A counter that grows on validation
instead of observation is data CI invented (rule 2), and two branches raising the same
counters conflict in the merge queue.

The distinction the store needs is the one the pipeline already makes elsewhere: a
**delivery stage** (the refresh merge that folds the gathered raw into the store) may land
data; a **validation pass** proves the tree is sound and lands nothing.

## What Changes

- `scripts/update_trending.py`: the refusals write is gated on a landing declaration
  (`declare_refusals_landing` / `refusals_landing_declared`, module seam) set from a new
  `--land-refusals` flag. Without it, `record_ingest_refusals` counts the refusals, prints
  them, and returns without touching the ledger; the per-file and run-total summaries say
  `NOT landed … no declared landing stage` instead of claiming a record that was never
  written. `--dry-run --land-refusals` is a contradiction (a dry-run writes nothing) and
  exits 2 naming both flags.
- `Makefile`: the delivery recipes `_merge`, `_merge-fetch` and the `_fix` merge carry
  `--land-refusals`; the validation recipes (`_validate-fetch`, `validate-data`) carry none.
- `tests/test_ingest_refusal_ledger.py`: the fixture declares the landing it simulates
  (`_fresh` = a `make merge` stand-in for the delivery), so #1148's guards still describe a
  delivery re-pass growing counters.
- `tests/test_refusals_land_declaration.py`: the new guards, driven through the REAL CLI over
  a REAL `git archive` + `git init` checkout, verdicted by `git status --porcelain`.

## Impact

- A validation pass (`make validate`, `make validate-data`, `--dry-run`, a test module, an
  implementation leg) leaves `data/refusals.json` — and, for `--dry-run`, the whole tracked
  tree — byte-identical, so an implementation PR carries only what its issue implements.
- The refresh delivery's refusal landing is unchanged (same records, same counters, same
  rule-3b growth), and every refusal is still printed in full: "refused N things, landed
  none" is a loud line, never a silent skip.
- The shipped ledger is NOT rewritten (rule 3b): the records the deliveries landed stay
  exactly as those deliveries left them.

## Not covered

- The counter inflation #1148 already collapsed (its records stand; only `seen_count`
  semantics changed there). Removing records is a rule-3b human decision.
- The `agents/skills/issue-implement` instruction to run
  `python3 scripts/update_trending.py` after a data change: it now lands nothing, which is
  correct for an implementation leg, but the line is a rule-6m smell (it reaches the script
  past the Makefile). Filed as a finding, not fixed here.
- Whether the delivery should re-ingest raw at all on a validation stage — the recipes still
  merge; only the refusal landing is now declared.
