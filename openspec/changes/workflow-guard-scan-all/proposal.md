# Scan every workflow .yml for the identity guard

**Issue:** [#816](https://github.com/andyholst/trending-local-llms/issues/816)
**Capability:** `agents-guard-registry`

## Why

§6j's guard (only the owner, a write+ collaborator, or `github-actions[bot]` may start
a pipeline; guard FIRST, before any secret) is exercised today only through
`tests/test_workflows.py`'s registry. No pipeline stage scans **every**
`.github/workflows/*.yml` and asserts the guard is in place **for the triggers each
workflow declares** — manual `workflow_dispatch`, cron `schedule`, `pull_request`,
`push`, `issues`, `workflow_run` — nor that a pipeline never waits on a human
(schedule bypass, no `environment:` approval gates). The owner's directive: a human
shall never have to accept a workflow pipeline; the guard decision starts it
mechanically, manually or automatically.

## What Changes

- `scripts/check_workflow_guards.py`: the ONE scanner — guard shape (own job, needs
  nothing, every other job needs it, no secrets), REAL guard scripts executed per
  caller class (owner / write+ collaborator / bot allowed; read-only, triage,
  non-collaborator, stranger re-run refused), `schedule` bypass present exactly when
  the workflow declares a cron, repository events admitted outright, and NO job may
  use `environment:`.
- Makefile seam `_check-workflow-guards` + public `check-workflow-guards`, bundled
  into the `lint:` recipe (rule 6m: `make lint` is already the first gate of
  `qa-validate`'s `validate` job and of `scripts/fix_loop.sh`).
- `tests/test_workflow_guards.py`: real tree green; planted fixture trees MUST red
  (no guard, guard behind a secret, job not needing the guard, cron without bypass,
  guard admitting a stranger, guard refusing the bot, `environment:` job).
- `tests/test_workflows.py` imports the scanner's caller classes + guard harness
  instead of owning copies (rule 6d).
- AGENTS.md §6j gains the no-human-approval clause + names the stage; §8 gains its
  row (rule 3c review declared on the issue). ARCHITECTURE.md §6 script row + §10
  regenerated.

## Impact

- Affected specs: `agents-guard-registry` (new tree-wide scan requirement).
- Affected pipelines: none dispatches anything new — `qa-validate.yml` runs it via
  `make lint` inside its existing `validate` job.
- Affected tests: new `tests/test_workflow_guards.py`; rewired `tests/test_workflows.py`.
- **Not covered:** repo-level GitHub settings (rulesets) are outside the tree; a
  ruleset approval gate is a human action, checked by hand, not by this stage.
