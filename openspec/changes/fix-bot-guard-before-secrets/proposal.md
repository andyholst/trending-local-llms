# The fix-bot guard is its own job, before any secret (issue #259)

**Issue:** [#259](https://github.com/andyholst/trending-local-llms/issues/259)
**Capability:** `bot-dispatch-guards`

## Why

AGENTS.md rule 6j says every bot pipeline carries the owner/collaborator guard
**as its FIRST job, checked BEFORE any secret**, and §8 lists "fix-bot reading a
secret before its guard" as a failure the trigger-guard test must catch -- but
`fix-bot.yml` did not do it and the test could not see that it didn't:

```yaml
jobs:
  fix:
    env:                                  # <-- JOB level, above the guard
      NOUS_API_KEY: ${{ secrets.NOUS_PORTAL_API_TOKEN }}
      FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
      HF_TOKEN: ${{ secrets.HF_TOKEN }}
      TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
    steps:
      - name: Owner / collaborator trigger guard   # <-- first STEP, not first JOB
```

A job-level `env:` holding `secrets.*` belongs to the **JOB**: the runner
materialises it when the job starts, so a guard that is merely the job's first
**step** does not run "before any secret" however early it sits. Fix-bot is the
pipeline that spends the Nous key and pushes with the owner PAT, so it is the
worst place for the check to be unenforceable -- and it *was* unenforceable: the
assertion in `tests/test_workflows.py` looked at **steps**
(`secret_steps = [i for i, st in enumerate(steps(fb)) ...]`), the job's own
`env` is invisible to it, and so the file could drift further from the rule with
no red at all.

## What Changes

- **`.github/workflows/fix-bot.yml`** -- the guard becomes its own job, FIRST and
  with **no `secrets.` anywhere in it** (only the default `github.token` it asks
  the collaborator-permission API with, which GitHub injects for the run and is
  not a repository secret). The work -- resolve, announce, checkout, images,
  smoke, the fix loop, the push -- moves to the `fix` job with `needs: [guard]`,
  which carries the four secrets at job level exactly as before. A refused caller
  now means the `fix` job never starts, so its secrets are never materialised.
- **`tests/test_workflows.py`**
  - `BOT_GUARDS` -- fix-bot's entry points at its `guard` **job** instead of its
    `fix` job, and the registry tightens to *every* guarded bot pipeline: the two
    that were missing (`code-review-bot.yml`, `queued-alarm.yml`) join it, so
    their guards are executed for every caller class too.
  - the new `test_guard_is_before_any_secret` proves for every entry that the
    guard job declares no secret, that no guard step touches one, that the guard
    job needs nothing, and that **every other job runs only after it**.
  - `test_owner_guards` asserts the fix-bot shape directly (own first job, no
    job-level secret, the `fix` job needs it and holds the secrets).
- **`AGENTS.md`** §6j states the enforceable form of the rule -- a job-level
  `env:` carrying `secrets.*` must live in a job that `needs` the guard -- and §8
  gains the guard's row.
- **`ARCHITECTURE.md`** gains fix-bot's `guard` job row and the asserted
  `needs: [guard]` on `fix`.

## Not covered

- **`qa-validate.yml` has no guard at all** (issue #279) -- it is the one pipeline
  left without one and it is fixed by its own change (`qa-validate-carries-the-guard`),
  not folded into this one.
- `code-review-bot.yml`'s secrets check being refused on every production run
  (issue #278) is its own issue: this change only makes its already-correct guard
  provable.
- A dispatch-only pipeline shipping broken because PR CI never executes it
  (issue #231) -- own issue, own change.
