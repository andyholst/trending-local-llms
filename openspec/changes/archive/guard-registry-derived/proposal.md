# The guard registry is derived from the tree, not remembered

**Issue:** [#313](https://github.com/andyholst/trending-local-llms/issues/313)
**Capability:** `bot-guards` (the owner/collaborator/`github-actions[bot]` trigger guard every pipeline carries)

## Why

`BOT_GUARDS` in `tests/test_workflows.py` is a literal tuple, and the three tests
that exercise the guard iterate over **that tuple only**:

- `test_guard_behaviour` (every caller class, the real guard script),
- `test_guard_is_before_any_secret`,
- `test_every_bot_guard_with_a_cron_has_the_schedule_bypass`.

Nothing asserted the tuple was **complete**, and it was not. Measured on
`master` before this change:

- `code-review-bot.yml` and `queued-alarm.yml` carried guards that
  `ARCHITECTURE.md` described and **no test ever ran** — they were missing from
  the registry entirely;
- `fix-bot.yml`'s entry named the `fix` job while the guard lived elsewhere.

The suite was green through all of it, and green **by construction**: a pipeline
that is absent from the registry is simply not in the "N passed". The guard is
the only thing between a stranger's `workflow_dispatch` and the live API keys, so
a registry that must be remembered is a registry that will be forgotten — and the
failure is silent exactly where a failure must not be.

## What Changes

- `tests/test_workflows.py` gains `_guard_step_index` / `discovered_guards` /
  `_dispatchable`: the guarded pipelines are **derived from the workflows
  themselves** (the same shape `_guard_step` already detects — a step whose name
  carries `guard`), so a guard nobody registered is still found.
- `test_the_guard_registry_is_derived_from_the_tree` checks the tree against the
  registry in **both** directions — a guarded workflow missing from `BOT_GUARDS`
  fails, and a registered pipeline that lost its guard step fails — plus they must
  agree on **which job** the guard is in (the `fix-bot` drift), plus the direction
  that protects the keys: **every workflow that can be dispatched carries a
  guard**. The registry becomes the record of the decision, not the input to it.
- `AGENTS.md` §8 gains the row, and the guard paragraph in §6j states that the
  tree is the input.

## Not covered

- The registry itself is kept: it still says *which* job each guard is in, and
  the caller-class tests still iterate it. This change makes forgetting to add an
  entry impossible, not the registry unnecessary.
- Whether a workflow that is **not** dispatchable needs a guard is not asserted:
  the rule is about who may START a pipeline, and only `workflow_dispatch` (and
  a re-run) is a start.
