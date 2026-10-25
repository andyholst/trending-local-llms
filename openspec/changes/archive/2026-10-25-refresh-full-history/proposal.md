# Proposal — refresh full history

Issue: #552

## Why

The refresh `aggregate` job is the pipeline's QA pass (`make qa-report` → `validate` + `test`), and it
ran it against a **shallow clone**: `actions/checkout@v4` defaults to `fetch-depth: 1` and
`refresh-bot.yml` set no depth anywhere. `make test` includes `check-commit-authorship`, which reads
`git log origin/master..HEAD`, so it failed there *by construction* on every refresh — measured on run
40126898852 (2026-10-24T19:47Z, reported **success**):

```
[qa-report] make test reported findings (rc=2); data still lands for review
=== FAIL: test_commit_authorship.py ===
  FAIL identity: the checkout carries the whole history (fetch-depth: 0)  [is-shallow-repository=true
```

The aggregate deliberately treats its QA pass as advisory, so a data PR still opens and CI repairs it.
That is sound only if a red there MEANS something. A permanently red check turns the whole pass into
noise: a real broken module or a data invariant looks exactly like the standing failure, and the run
list shows a green job. This is the "the refresh fails sometimes and nobody notices" shape.

## What changes

- `refresh-bot.yml`'s `aggregate` checkout asks for the full history (`fetch-depth: 0`), with the
  measured failure in the comment so the next reader knows why it is not a default.
- `tests/test_workflows.py` gains a guard: every job that runs `make test`, `make qa-report` or
  `make check-commit-authorship` must check out with `fetch-depth: 0`. Comment-only mentions are not
  calls, so prose does not trip it.

## Impact

- `.github/workflows/refresh-bot.yml` (one checkout option), `tests/test_workflows.py` (one guard).
- No make target, script, job or image changes, so `ARCHITECTURE.md` is unchanged.

## What is NOT covered

- The aggregate still treats a red QA pass as advisory (it opens the data PR anyway, by design). What
  changes is that a red there now means a real failure instead of a checkout-shape one.
- The other refresh jobs (the four search legs) keep the default depth: they write raw snapshots and
  run no `git log` guard.
