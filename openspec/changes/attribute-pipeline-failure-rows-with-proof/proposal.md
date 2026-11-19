# Proposal: attribute-pipeline-failure-rows-with-proof

Issue: #1053

## Why

Rule 6r says a fixed pipeline failure must raise its ledger row (`data/pipeline_failures.json`)
with `fix_pr` + `guard`. The landed mechanism (`stamp_merged_fix_prs`,
`scripts/pipeline_failure_issue.py:728`, PR #1099) can only do that for a row whose issue a
**merged, `tests/`-guard-carrying PR closed**. Issue #1053 names ten diagnosed rows; seven are
already attributed that way (#1082 ×4, #1057, #955, #922), but three — run `42976201014`
(issue #826, `queued-alarm`/`alarm`, `Makefile:1359: sweep-alarm`), `42977708147` (issue #827)
and `43047130543` (issue #828), both `issue-bot`/`implement`, `Error 3` at `_implement-issue`
followed by `[verdict] REFUSED: triage.md does not exist` — sit behind an `agent:refined` verdict
hold (rule 6j: a decided hold has NO expiry). Their issues will never be closed by a fix PR, so
the landed stamp can never reach them: a re-diagnosed row that names no `fix_pr`/`guard` stays a
live failure with no way to record a landed fix, and `make pipeline-failure-guard-check` can only
ever report it.

## What Changes

- A new attribution seam, `make pipeline-failure-attribute` (`scripts/pipeline_failure_attribute.py`),
  which raises `fix_pr`, `fix_pr_merged_utc`, `guard` (only when the row names none already),
  `attributed_utc` and `attribution_note` onto a diagnosed ledger row **from an attestation, not
  from a closing PR** — the path the merged-PR stamp cannot take for an issue held by a verdict.
- Every stamp is proven mechanically before it is written: the fix PR is read live through the real
  `gh` client and must be `merged` (its merge SHA recorded); the guard must pass the ONE
  collected-guard seam `guard_test_exists` in `scripts/pipeline_failure_guard_check.py`; the
  attestation's `EVIDENCE:` must pass the ONE evidence gate `evidence_is_checkable` in
  `scripts/issue_verdict.py`; and the row must already carry a diagnosis (`error_excerpt`, not
  `log_expired`) — an undisagnosed row cannot be attributed, because a value that cannot be traced
  is invented (rule 2).
- A report mode that prints every diagnosed-but-unattributed row with its run, issue, targets and
  the reason no stamp is possible yet, so the ledger's unattributed tail is visible on the sweep
  instead of silently waiting for a closing PR that will never come.
- Append-only (rule 3b): keys are ADDED, a recorded `guard` is never overwritten, a row already
  naming a `fix_pr` is never re-pointed, and the diagnosis fields are never shrunk.
- The seam is wired where a ledger change can land: `queued-alarm.yml` runs it (report mode each
  sweep; stamp mode from owner-supplied dispatch inputs) before the existing ledger-PR landing
  step, so a stamped row rides the same reviewed ledger PR as a new diagnosis (rule 6d/6m).

## Impact

- `scripts/pipeline_failure_attribute.py` (new) — the attribution decision (rule 6d: one
  implementation, reached only through `make pipeline-failure-attribute`).
- `Makefile` — `pipeline-failure-attribute` target following the `pipeline-failure-*` pattern.
- `.github/workflows/queued-alarm.yml` — the attribution step (report each sweep; stamp on owner
  attestation), placed before the ledger-PR landing step.
- `tests/test_pipeline_failure_attribute.py` (new) — drives the real script against recorded `gh`
  fixtures and planted ledgers (rule 6m: external system only, no `scripts/` monkeypatching).
- `AGENTS.md` §6r gains the attribution seam in the chain description and §8 gains the guard row.

## Not covered

- It never invents an attribution: a row whose class has no landed, guard-carrying fix stays
  `fix_pr: null` and its issue stays open as a live failure.
- It never closes an issue and never writes a label (rule 6j: a verdict is the reviewer's or a
  human's).
- It does not rewrite history: `undiagnosed`, `rediagnosed_utc`, `error_excerpt` and every existing
  ledger field stay exactly as recorded.
