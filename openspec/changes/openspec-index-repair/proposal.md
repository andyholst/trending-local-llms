# Event-driven keeper for a red master index gate

**Issue:** #304
**Capability:** `openspec-index` (the generated `OPENSPEC.md`, its guard, and the
pipeline keeper that repairs index drift the moment a merge causes it).

## Why

`make openspec-check` is a gate of qa-validate's `validate` job, and `validate`
runs on a **push to master** too. Every merged PR archives its OpenSpec change
(rule 6f), so `master`'s tree no longer matches the committed generated
`OPENSPEC.md`, and the push-to-master `validate` goes red **by construction** —
with no PR-side repairer (rule 6q: every repair path needs a PR, and auto-merge
needs the very run that just went red). Measured 2026-11-12: pushes `28f2cd3`
and `ce57e9b` both went red at the OpenSpec gate, auto-merge stayed blocked
repo-wide for every other open PR, and the only keeper — architecture-bot, cron
`13 * * * 3`, Wednesday-only — had hours to days to act. The stale-index failure
class recurs on EVERY merge; an alarm that merely shouts (rule 6q's
`make master-alarm`) does not unblock the queue.

## What Changes

- `scripts/openspec_index_repair.py` — the ONE classifier+repair:
  `--classify-and-write` prints the verdict `DRIFT=none|index-only` (rule 6d),
  regenerates `OPENSPEC.md` through the existing generator when the drift is
  index-only, re-verifies with the generator's own check, and exits 2 (loudly)
  when the committed index exists but cannot be read — never a silent clean.
  `--print-pr-body` composes the keeper PR body: no closing keyword, it records
  drift and `refs` #304 (rule 6e).
- Two new Makefile targets wire it: `openspec-index-repair`,
  `openspec-index-repair-pr-body` (host seams like `architecture-pr-body`).
- qa-validate grows an `index-repair` job: `needs: [guard, validate]`, runs only
  on a FAILED push to master. It asks the script for the verdict and re-decides
  nothing: a keeper PR lands only when the verdict is `index-only`, only from a
  working tree whose drift touches `OPENSPEC.md`/`openspec/**` (a non-index drift
  is refused at the workflow boundary), on branch
  `ci/openspec-index-repair-<UTC>` (timestamped — no issue number, the #852
  discriminator stays inert), commits as the repo agent (rule 3f), and never
  merges anything.
- `scripts/master_alarm.py`'s GATES registry re-names the `openspec-check`
  keeper: `qa-validate index-repair + architecture-bot` (event-driven keeper,
  weekly backstop); `tests/test_master_alarm.py` pins the mapping per gate so a
  new keeper cannot name an imaginary pathway.
- `tests/test_openspec_index_repair.py` (new suite, auto-discovered by
  `scripts/run_tests.sh`) + a qa-validate job-contract test in
  `tests/test_workflows.py`.

## Impact

- **Pipeline:** qa-validate gains one job; a red `openspec-check` on master
  self-repairs within minutes instead of waiting for Wednesday.
- **Data:** none. No model, measurement, or contract key changes.
- **AGENTS.md:** §6q gains the event-driven-keeper paragraph; §6b's
  `qa-validate.yml` row names the `index-repair` job (rule 3c review-required
  row: the change adds a keeper, it removes no rule).

## NOT covered

- A red `openspec-check` on a PR event stays red for the §6s sweep or a human
  (the keeper is master-only by design; a keeper PR may not trigger its own
  repair).
- Drift that is NOT index-only (tasks/proposal/specs edits landed unarchived,
  malformed change directories): the classifier refuses loudly and the workflow
  lands nothing — that is a human/fix-loop repair, not an auto-regeneration.
- The stale `HOURLY` comments inside `architecture-bot.yml` (its cron is
  Wednesday-only): filed as separate tech-debt, fixed in its own change (rule
  6g).
