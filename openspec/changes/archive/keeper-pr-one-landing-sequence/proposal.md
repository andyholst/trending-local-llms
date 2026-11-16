# Proposal: keeper-pr-one-landing-sequence

## Why

The keeper-PR job shape — the reviewed PR that LANDS a generated-file repair the
pipeline just computed — is hand-written three times in the workflows:
`index-repair` and `architecture-repair` in `qa-validate.yml` and the ledger PR
in `queued-alarm.yml`. Each copy re-implements the same landing sequence:
nothing-to-land short-circuit, the refuse-if-more-than-one-file guard, the
branch + agent identity + one commit + push, the body from the keeper's own
`*-pr-body` target, the `gh pr create` with no closing keyword — and two of
them separately re-spell the #960 mergeable-only keeper dedupe. When #960 fixed
the dedupe discriminator, it had to be re-typed into each shell by hand; the
third (the ledger keeper) has no dedupe at all and no porcelain guard. Three
copies of one procedure is the drift rule (AGENTS.md rule 6j/6d) applied to CI.

## What Changes

- NEW `scripts/keeper_pr.py`: the ONE keeper-landing sequence — nothing-to-land
  (exit 0), refuse-extra-changes (exit 1), opt-in #960 mergeable-only dedupe,
  timestamped branch from the current tip with the repo agent identity, ONE
  commit touching only the keeper's file, push, body produced by the keeper's
  own `make <BODY_TARGET>`, opened with `gh pr create` (no closing keyword),
  failure to run is exit 2.
- NEW `make keeper-pr` (internal `_keeper-pr` recipe + public wrapper),
  parameterized by `FILE`, `BRANCH_PREFIX`, `COMMIT_MESSAGE`, `PR_TITLE`,
  `BODY_TARGET`, `BODY_ARGS`, `DEDUPE`.
- The three keeper jobs' Land steps become one `make keeper-pr …` call each;
  the hand-written shell sequences are deleted.
- NOT covered: the verdict decisions themselves (`openspec_index_repair.py`,
  `architecture_block_repair.py`, the ledger filer stay the classifiers — rule
  6d); the keeper body texts (stay in their own `*-pr-body` targets); adding
  dedupe to the ledger keeper (its semantics differ per issue #802: each
  sweep's append is its own record).

## Impact

- **System:** `.github/workflows/qa-validate.yml` (index-repair, architecture-repair),
  `.github/workflows/queued-alarm.yml`, `Makefile`, new `scripts/keeper_pr.py`,
  `ARCHITECTURE.md` (§6 row + target table row).
- **Coverage:** `make keeper-pr` is called by all three keeper jobs (rule 6m
  both directions: the script is reachable from a target CI runs, and the
  target is called by CI).
- **Risk:** the keeper jobs' visible log lines change wording; behavior is
  preserved (same guards, same branch shapes, same bodies). The ledger keeper
  gains the porcelain guard (it previously committed whatever had changed).

## Issue

Issue: #869
PR: #1082
