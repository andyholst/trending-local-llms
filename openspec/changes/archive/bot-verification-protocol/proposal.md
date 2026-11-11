# The bot verification protocol — one bot at a time, guarded, verified after merge

**Issue:** [#279](https://github.com/andyholst/trending-local-llms/issues/279) (the guard audit; this change documents the protocol it belongs to)
**Capability:** `bot-verification-protocol`

## Why

The repo owns eight bot pipelines and documents, in detail, *what* each one does
and *who* may start it (AGENTS.md §6b `Who can run what`). What it never states
is the **order in which they are exercised** and **what "verified" means**:

- bots are exercised ONE at a time — an audit that runs several at once cannot
  tell which pipeline produced a failure, and the whole reason the guard exists
  is that a run has ONE caller;
- a defect found on a bot is fixed on a branch where the fix is proved the way
  every other change is — the pipelines are wired to the Makefile and the
  Makefile targets are tested with NO mocks by the unit tests `ci.yaml` runs —
  so the PR carries the fix AND the regression guard that would have caught it;
- the next bot's cycle starts only when the current PR's `guard` and `validate`
  jobs are green;
- once every PR is open and fixed, the merges are waited on: a PR lands only
  through qa-validate's `auto-merge` job (never `--admin`, never a hand merge);
- and **no PR is "verified" until it is MERGED** — verification is a second,
  equally sequential pass: re-dispatch each merged bot on its own and confirm the
  fix holds in production before starting the next.

None of that was written down, so it lived only in the head of whoever ran the
audit. A protocol nothing can check rots on the first reorder of a job.

## What Changes

- `AGENTS.md` §6b gains the **Bot verification protocol — one bot at a time**
  block: the order (one bot per cycle), the fix-PR contract (fix + regression
  guard, tested no-mocks by the tests `ci.yaml` runs), the gate (green `guard` +
  `validate` before the next bot), the merge rule (only `auto-merge`, never
  `--admin`), and the verification pass (re-dispatch each MERGED bot, one at a
  time), all under the guard every start already carries.
- `tests/test_workflows.py::test_bot_verification_protocol_is_documented_and_guarded`
  ties the prose to the machinery: it fails when the protocol leaves the
  document, and it re-proves, for every pipeline the protocol names, that the
  guard is the FIRST step of the job that carries it — so a reordered job turns
  the protocol red instead of silently invalidating it.

## Not covered

- The protocol does not re-specify the guard itself: `BOT_GUARDS`,
  `test_guard_behaviour` and `test_every_bot_guard_with_a_cron_has_the_schedule_bypass`
  already own that, and this change delegates to them rather than restating them.
- `qa-validate`'s own missing guard is issue #279 and its own change
  (`qa-validate-carries-the-guard`); this change documents the rule that makes
  the omission a defect, it does not fix that pipeline here.
