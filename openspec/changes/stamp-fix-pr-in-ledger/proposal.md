# Stamp `fix_pr` + `guard` into the pipeline-failure ledger when a fix PR merges (Issue: #1099)

Issue: #1099

## Why

`make pipeline-failure-guard-check` refuses a ledger row whose issue is CLOSED while the row names no `fix_pr` and no `guard` test (rule 6r) — and NO leg ever raises those fields when a fix PR merges. Measured at filing (issue #1099): not one row in `data/pipeline_failures.json` carried `fix_pr`. Every closed row so far was rescued by a manual keeper cycle (the #833 keeper `keeper-pipeline-ledger-raise-833` hand-raised `fix_pr: 1057`; the #820–#829 rows were raised by `classify-nov15-red-ledger-rows`). That makes the gate's refusal a permanent alarm with no satisfiable automated path: the fix lands, the PR merges, the issue closes — and the ledger row stays `fix_pr: null` until a human or a keeper notices. Because the gate is a `master_alarm.GATES` member of qa-validate's `validate` job, a stale row reds every push-to-master and blocks auto-merge repo-wide (rule 6q: a red push gate has no repairer).

## What Changes

- `scripts/pipeline_failure_issue.py` gains the **stamp pass**: `issue_close_refs` / `pr_close_view` read each closed row's issue through `scripts/pr_closure.py`'s own closing parser and GitHub's timeline; `diff_guard` picks the guard module from the merged closer's diff (the earliest ADDED `tests/test_*.py`, preferring a recorded `guard`); `stamp_merged_fix_prs` raises `fix_pr` + `guard` + `merged_utc` + `stamp_utc` + `stamp_note` onto the row (additive only — rule 3b: nulls filled, keys added, nothing shrunk); `compose_stamp_comment` / `post_stamp_comment` post ONE marker-deduplicated annotation on the issue carrying the registered `pipeline-ledger-stamp` marker. An OPEN issue stays in-flight and untouched; an ambiguous close (two merged closers) and a guard-less merged close stay INDETERMINATE and unstamped — the gate stays RED on them, never guessed. A failed per-row read is loud and retried next sweep, never a crash and never a fake clean.
- `scripts/bot_markers.py`: `LEDGER_STAMP_NAME = "pipeline-ledger-stamp"` registered as `REGISTRY["queued-alarm"]["stamp"]`, with the shape in `ledger_stamp_marker` / `parse_ledger_stamp_run` — writer and dedup reader share ONE spelling (rule 6j).
- `Makefile`: `pipeline-failure-issue` gains the stamp pass behind the SAME target (no new target, rule 6m); the swept ledger append is landed as a ledger PR exactly as the filer's own append is landed today.
- `AGENTS.md` §6r states the stamp pass and §8 gains the guard row (this change is attended: the owner directive of 2026-11-18 signs off the rulebook diff).

## Impact

- Rule 6r's raise lands automatically through `make pipeline-failure-issue` inside the `queued-alarm` sweep: a merged, guard-carrying fix PR clears its ledger row without a keeper cycle, keeping `pipeline-failure-guard-check` — hence auto-merge — green.
- Ledger shape unchanged: the pass fills fields the filer already declares (`fix_pr`, `guard`), matching the manually raised rows #800/#820–#829/#833.
- No pipeline, contract, or data-store change; the filer still never fixes anything (rule 6g).

## Not covered

- Stamping AGENTS.md rulebook rows (protected; rule 3c human sign-off stands).
- Renaming or migrating guard modules: a raised `guard` that stops existing re-opens the row (the guard-gate test pins that), and re-naming is the re-diagnosis pass's job (#969/#986), not this one.
- Ledger rows whose issue was closed by a HUMAN without any closing PR: those stay the keeper's act, reported, never stamped.
