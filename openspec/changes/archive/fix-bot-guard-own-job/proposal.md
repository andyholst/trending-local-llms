# The fix-bot guard is its own job, before any secret

**Issue:** [#259](https://github.com/andyholst/trending-local-llms/issues/259) — `fix-bot` declares its secrets at JOB level above the guard step, so the guard is not "before any secret" as rule 6j requires
**Capability:** `bot-dispatch-guards`

## Why

Rule 6j says the owner/collaborator guard runs **as its FIRST job, checked BEFORE any secret**, and §8 lists "fix-bot reading a secret before its guard" as a failure the trigger-guard test must catch. `fix-bot.yml` did neither, and the assertion could not see it:

```yaml
jobs:
  fix:
    env:                                  # <-- JOB level, ABOVE the guard step
      NOUS_API_KEY: ${{ secrets.NOUS_PORTAL_API_TOKEN }}
      FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
      HF_TOKEN: ${{ secrets.HF_TOKEN }}
      TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
    steps:
      - name: Owner / collaborator trigger guard   # <-- first STEP, not first JOB
```

A job-level `env:` holding `secrets.*` belongs to the **JOB**: the runner materialises it when
the job starts, so a guard that is merely the job's first *step* does not run "before any
secret" however early it sits. Fix-bot is the pipeline that spends the Nous key and pushes with
the owner PAT — the worst place for the check to be unenforceable, and it *was* unenforceable:
the assertion read **steps** only (`secret_steps = [i for i, st in enumerate(steps(fb)) …]`), so
the job's own `env` was invisible to it and the file could drift further with no red at all.

Two further gaps in the same registry: `BOT_GUARDS` pointed fix-bot at its **`fix` job** (not a
guard job at all), and it omitted `code-review-bot.yml` and `queued-alarm.yml` entirely — both
of which carry guards, so **their guards were described in `ARCHITECTURE.md` and executed by
nobody**.

## What Changes

- **`.github/workflows/fix-bot.yml`** — `guard` becomes its own FIRST job, declaring **no
  `secrets.` anywhere** (only the default `github.token` it asks the collaborator-permission API
  with, which GitHub injects for the run and is not a repository secret). The work — resolve,
  announce the window, checkout, images, `hermes-smoke`, the fix loop, the push — moves to the
  `fix` job with `needs: [guard]`, carrying the four secrets at job level exactly as before. A
  refused caller now means the `fix` job never starts, so its secrets are never materialised.
- **`tests/test_workflows.py`**
  - `BOT_GUARDS`: fix-bot's entry points at its `guard` **job**, and the registry gains
    `code-review-bot.yml` + `queued-alarm.yml`, so every guarded pipeline's guard is EXECUTED for
    every caller class rather than merely described.
  - `test_guard_is_before_any_secret` (new): for every entry — the guard job declares no secret,
    no guard step touches one, the guard job needs nothing, and **every sibling job `needs` it**.
  - `test_owner_guards` asserts the fix-bot shape directly.
- **`ARCHITECTURE.md`** — fix-bot's `guard` job row, and `needs: [guard]` on `fix`.

## Not covered

- **The `AGENTS.md` §6j sentence and §8 row for the JOB-level distinction** (rule 6c) are **owed,
  not written**: `AGENTS.md` is a protected rule file whose write approval has not returned.
  Recorded in `findings.md` and filed as its own issue, exactly as #212 and #310 do — never
  worked around, never ticked untruthfully. This is narrower than it sounds: #283's §8 row
  already covers "a `needs: guard` missing from a job that reads a secret", so the behaviour is
  described; what is missing is the sentence that a job-level `env:` is materialised at JOB start,
  which is precisely why the old step-level assertion was blind.
- **The hand-maintained registry** found while writing this (`BOT_GUARDS` is a literal tuple and
  nothing asserts it is complete — which is *how* `code-review-bot.yml` and `queued-alarm.yml`
  went unnoticed) is filed as its own finding, not fixed here (rule 6g).
- **`qa-validate.yml`'s guard** landed separately (#283); this change only stops the registry
  from mis-pointing fix-bot.
