# The implementer decides on a bare runner and reads the repo only after it checks it out

**Issue:** [#281](https://github.com/andyholst/trending-local-llms/issues/281)
**Capability:** `issue-bot` (the implementer pipeline)

## Why

Measured on the first sweep that had something to do (issue-bot run **38835373137**,
schedule, 2026-10-16T01:29Z):

```
2/19  Resolve the issue (open, labelled, one branch per issue)  FAILURE
      make: *** No rule to make target 'issue-thread'.  Stop.
3-18  Checkout master / base-check / images / smoke / announce / implement /
      push / PR / fix loop / findings / report                 SKIPPED
```

`.github/workflows/issue-bot.yml` runs `make issue-thread` in the **Resolve the
issue** step (continuation of `8a3469f`, issue #210) which sits *above*
`Checkout master` — on a bare runner there is no Makefile, so the implementer
died at step 2 and every step that would have implemented something was skipped.
The Makefile does define the target (`issue-thread:`, line 771); the workspace is
what was missing.

The breakage was invisible for as long as the queue was empty (`implement` is
skipped when nothing was picked) and surfaced the moment a data-gap issue became
pickable — i.e. one sweep after #280 restored the label the queue keys on. That
is the whole point of the pipeline: the bot whose job is to turn a filed issue
into a PR could not implement anything, and nothing said so.

`tests/test_workflows.py::test_issue_bot` asserts triggers, gates, tokens,
concurrency and step names, but never that the repository exists before a step
runs a repo target. Nothing else did either.

## What Changes

- The `Resolve the issue` step becomes **decision only** (`gh` reads the issue's
  state and title, computes the branch, sets `implement`/`issue`/`branch`), so it
  needs no workspace — and the `Checkout master` step can keep being gated on its
  output (`steps.iss.outputs.implement == 'true'`), which is why the checkout
  cannot simply move to the top.
- Reading the WHOLE thread (`make issue-thread`, issue #210) moves into its own
  step **after** the checkout — placed after `Hermes routing smoke`, before the
  reporter window and the implementation — and fails loudly when `issue.md` is
  empty (a run with no thread would implement a specification it never read).
- A class guard in `tests/test_workflows.py`
  (`test_a_step_that_calls_make_runs_after_the_checkout`): in EVERY workflow,
  EVERY step whose `run` calls a `make` target must come after its job's
  `actions/checkout`; a job that calls `make` with no checkout at all is a
  finding. Verified red against `origin/master`'s `issue-bot.yml`.
- `AGENTS.md` §8 gains the guard's row; §6e's issue-bot description notes that the
  resolver is repo-free by design.

## Not covered

- The live confirmation (the next sweep implementing an issue end to end) is a
  run, not a test; it is reported on #281 after this merges.
- `make issue-thread` itself is unchanged — it was never broken.
