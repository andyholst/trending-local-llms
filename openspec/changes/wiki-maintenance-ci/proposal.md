# Proposal: wiki-maintenance-ci

Issue: #1773

## Why

The written docs are generated from the data store, but nothing checked that they
STAYED in step: a stale `Last generated` stamp, a README row for a model the store
no longer holds, or an `ARCHITECTURE.md` inventory line naming a deleted script
could sit green until a human noticed. Rule 6t leaves `refresh-bot.yml` as the only
scheduled pipeline, so a new cron or a second workflow was not an option — the
checker had to ride that existing cadence as one job.

## What Changes

- Add `scripts/wiki_maintenance.py`: an offline, deterministic checker that derives
  truth from `data/models.json` (canonical model names + `generated_utc`), the
  generated `README.md` render and the `ARCHITECTURE.md` inventory block, and
  reports every stale/false claim with the exact file+needle (UPDATE) and every
  obsolete doc with evidence (ARCHIVE). `--check` is the gate; `--apply` prints a
  keeper PR body and never mutates a doc. No network, no model call.
- Add `_wiki-maintenance` / `wiki-maintenance` and `_wiki-maintenance-check` /
  `wiki-maintenance-check` Makefile targets following the internal-recipe /
  public-wrapper pattern, both routed through the single python-env seam.
- Add ONE `wiki-maintenance` job (`needs: guard`, `contents: read`) to the existing
  `refresh-bot.yml` schedule — NO new `on.schedule` block and NO new workflow.
- Add `tests/test_wiki_maintenance.py` with RED-first planted-doc tests (current
  tree green, stale/obsolete RED) plus wiring, keeper-body and unreadable-tree guards.
- Add `findings/1773-ci.md` with the Evidence/Why/Done-when analysis and the §8
  Owed-row for the new guard.

## Impact

No data format, contract, image or model-call change. The checker is read-only: `--check`
only reports and gates; `--apply` only prints to stdout. The job carries no secret
and no owner PAT. The architect's weekly review is the consumer of a RED finding.
No doc outside the strict change scope (AGENTS.md, ARCHITECTURE.md, README, data,
agents/*, host profiles, other lanes' files) is edited by this change.

## Not covered

- No new cron, no dispatched workflow, no merge or master push, no collaborator
  grant, no automatic doc rewrite by the pipeline.
