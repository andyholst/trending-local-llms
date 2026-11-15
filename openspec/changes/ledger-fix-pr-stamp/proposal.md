# Ledger raise: recording the completing PR stamps the pipeline-failure row (Issue: #1068)

Issue: #1068

## Why

`data/pipeline_failures.json` records every diagnosed pipeline failure; rule 6r says "the fix PR raises its ledger row (append-only) with `fix_pr` + `guard`". No leg did the raise: PR #1057 merged the fix for issue #833, its ledger row stayed `fix_pr: null`, and the next master push (run 43761917321) red at `make pipeline-failure-guard-check` — blocking auto-merge repo-wide until the manual keeper PR #1067 raised the row. Every future pipeline-failure fix would repeat this.

## What Changes

`make openspec-record-pr ISSUE=<n> PR=<m>` — the moment the implementer records its PR — also raises the ledger row(s) for issue #<n>: `fix_pr: null` → `fix_pr: <m>`; `guard` KEPT when the row already names one, FILLED from the change's own `- **Test:** tests/test_*.py` references when null; and a row that needs a stamp with NO resolvable guard REFUSES the entire recording (exit 2, nothing mutated). Issues with no ledger row record exactly as before.

## Impact

- `scripts/openspec_record_pr.py` — the stamp (plan before mutation, apply after recording; additive only, rule 3b).
- `tests/test_ledger_fix_pr_stamp.py` — new suite locking every shape.
- `ARCHITECTURE.md` §targets + §6 rows and the regenerated §10 line (rule 6h).
- Capabilities: `openspec-lifecycle`.
- No new `make` target: the stamp rides the already-wired `openspec-record-pr` (issue-bot step "Record the PR on the change", rule 6m).

## Not covered

- Retro-stamping rows whose fixes merged before this seam exists — the manual keeper path (PR #1067) stays the remedy, and `pipeline-failure-guard-check` keeps reds visible.
- The re-diagnosis pass (`rediagnosed_utc`), unchanged.
