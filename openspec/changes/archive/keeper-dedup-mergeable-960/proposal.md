# Proposal: keeper-dedup-mergeable-960

Issue: #960 — "an unmergeable (DIRTY) keeper PR suppresses the keeper repair it
PR: #961
was supposed to land"

**Capability:** `keeper-repair`

## Why

qa-validate's event-driven keeper jobs (`index-repair`, `architecture-repair`,
rule 6q) file a `ci/…-repair-<UTC>` keeper PR when a push to master goes red on
a generated-artifact gate, then suppress duplicates while "one keeper per drift"
is open. The dedup counted an open keeper by branch prefix ALONE. Measured on
run 43610043055 (push `aec1410`, 2026-11-14): master was red at
`openspec-index-check` ("OPENSPEC.md is stale or missing (3 active, 280
archived on disk)") for the THIRD consecutive push, and the `index-repair` job
ended GREEN having filed nothing — "An index-repair keeper PR is already open" —
because the only match, PR #956, was `mergeStateStatus=DIRTY`: a conflicting
keeper builds no merge commit, runs no workflow, and lands nothing. The red had
no repairer until an unrelated PR merged and happened to carry the fix.

## What Changes

- Both keeper dedup steps in `.github/workflows/qa-validate.yml` read
  `mergeStateStatus` beside the branch prefix: only **mergeable** open keepers
  suppress a new keeper PR. A DIRTY/CONFLICTING keeper is named
  `UNMERGEABLE` in the job log and a fresh keeper is filed against the current
  master tip.
- New regression `tests/test_workflows.py::test_keeper_dedup_counts_only_mergeable_keepers`
  pinning both jobs' dedup shape (RED on the pre-change workflow — 6 named
  checks).
- `AGENTS.md` §6q states the mergeable-only discriminator (rule 3c disclosure
  comment lives on issue #960), plus its §8 guard-table row.

## Impact

- `.github/workflows/qa-validate.yml` (two run-steps in `index-repair` and
  `architecture-repair`; no new job, no new target, no secret-shape change).
- `tests/test_workflows.py` (one test + its registration).
- `AGENTS.md` (§6q paragraphs, §8 guard row).

## Not covered

- No auto-close of a DIRTY keeper PR (closing another agent's PR stays a human
  act); the fresh keeper supersedes it in practice.
- No change to the verdict scripts (`openspec_index_repair.py`,
  `architecture_block_repair.py`) — the classification stays theirs (rule 6d).
- No change to `architecture-bot`'s weekly cadence.
