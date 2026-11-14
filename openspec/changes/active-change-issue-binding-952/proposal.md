# Proposal: active-change-issue-binding-952

Issue: #952 — "the sweep's OpenSpec change must bind the Issue it implements
BEFORE the record step — a refused openspec-record-pr wasted the 2026-11-12
weekly sweep delivery"

**Capability:** `openspec-change-binding`

## Why

The lifecycle rule (AGENTS.md §6f) closes a change through the PR that closes
its issue: `make openspec-record-pr ISSUE=<n>` finds the change by its
proposal's `Issue:` line. An implementation run that creates its change
without that binding hits nothing until the record step at the END of the
run — measured on the 2026-11-12 weekly `schedule` sweep of `issue-bot.yml`
(run 43147959554, step 15): ~30 minutes of implementation, then
`[openspec-record-pr] REFUSED: no change — active or archived — references
  #624 — nothing recorded`, a `failure` delivery, and `make sweep-alarm`
reds every queued-alarm until a newer schedule delivery replaces it (manual
dispatch run 43599292096, 2026-11-14). The refusal is correct; noticing it
last is the defect.

## What Changes

- New deterministic gate `make openspec-binding-check`
  (`scripts/openspec_binding_check.py`), the ONE implementation of the verdict:
  - every ACTIVE change (everything except `archive/`) must bind an Issue —
    `Issue:` parsed through `openspec_index._refs`, the ONE proposal parser
    (rule 6d), so `Issue: #650` and `**Issue:** [#715](https://…)` are the
    same state;
  - an ACTIVE change that genuinely implements no issue (the keeper shape,
    rule 6e) must DECLARE it — a `Binding-exempt: <reason>` line — which is
    reported, never silent; the eight archived changes with no `Issue:` line
    show silence can never be the default;
  - a change that is neither: **exit 1**, naming each with the exact remedy;
  - a `--changes-dir` fixture seam; a tree that cannot be read is a loud
    **exit 2**, never a vacuous clean.
- `openspec-binding-check` becomes a PREREQUISITE of `make openspec-check`,
  the gate family qa-validate already runs on every PR and push — and that
  the implementer's own fix loop re-runs — so an unbound change goes red
  while the run can still repair it (rule 6d: bundled, no new job).

## Impact

- `scripts/openspec_binding_check.py` (new), `Makefile` (.PHONY list, the new
  target, the `openspec-check` prerequisite line),
  `tests/test_openspec_binding.py` (new suite), `AGENTS.md` §6f + §8
  (rule-3c declared diff on issue #952), `ARCHITECTURE.md` §6 rows +
  regenerated inventory, `.hermes/skills/issue-implement` (the binding is
  written at change creation, not discovered at record).
- CI: no new job — the existing `validate` job's `make openspec-check` step
  now also executes the binding check.

## Not covered

- The sweep's root cause that red `make sweep-alarm` (the failed 11-12
  schedule delivery) stays until the next weekly delivery lands or #952's
  class is repaired live — this change prevents the recurrence, it does not
  rewrite history.
- Retrospective binding of the eight archived unbound changes: out of scope
  (rule 3b, archives are history).
