# Keeper: classify the five Nov-15 red-run ledger rows onto their landed guards (Issue: #1039, #1040, #1041, #1042, #1043)

Issue: #1039, #1040, #1041, #1042, #1043
Binding-exempt: keeper — a data classification observed while diagnosing the ledger's null `fix_pr` rows; this change implements no open issue and closes none (the issues close on ledger proof via `make issue-verdict` after this lands).

## Why

Five ledger rows carry `fix_pr: null` beside OPEN issues (#1039–#1043, all in the bot queue). Each was diagnosed from a run log, and each failure class is ALREADY fixed and guarded by merged changes — but the ledger does not say so, so the issues sit actionable and the `#993` close-with-proof verdict (`make issue-verdict`) refuses to close them (`EVIDENCE: data/pipeline_failures.json run=<id>` is checkable only when the row names a merged fix PR and a guard test `make test` collects).

The log diagnosis (run-job step names, not the filer's quoted lines):

- Runs 43716345030, 43716362366, 43718826142, 43725338063 (Nov 15 12:56–14:37, qa-validate `validate`) each failed the **OpenSpec gate**: `OPENSPEC.md is stale or missing (the generated index does not list every change on disk) — make openspec-index` → `make: *** [openspec-index-check]` — the stale-generated-index drift on `master` pushes. The repair chain for this class landed in three merged steps: `24c6675` (event-driven `index-repair` keeper job), PR #961 (keeper dedup honours only mergeable keepers — the DIRTY keepers of Nov 14 were suppressing fresh ones while these runs went red), and PR #1082 (one keeper-PR landing sequence through `make keeper-pr`). The class self-repairs today: the Nov 16 drift red at head `415975a` (run 43906781401) was repaired by keeper PR #1096 through exactly that sequence. Guard: `tests/test_openspec_index_repair.py`.
- Run 43147240875 (Nov 12 03:17, queued-alarm) failed `owed-rows-check` with `exit 2` naming two MALFORMED/UNREADABLE owed-row markers. PR #922 (`fix(tech-debt): implement #766`, merged Nov 14) rewrote the marker read and close-note path in `scripts/owed_rows_check.py` with `tests/test_owed_rows.py`; the live gate is green on the current tip (landed=4 outstanding=3 problems=0, exit 0). Guard: `tests/test_owed_rows.py`.

## What Changes

- `data/pipeline_failures.json`: the five entries gain their `fix_pr` and `guard` — rows 43716345030 / 43716362366 / 43718826142 / 43725338063 get `fix_pr: 1082`, `guard: "tests/test_openspec_index_repair.py"`; row 43147240875 gets `fix_pr: 922`, `guard: "tests/test_owed_rows.py"`. Additive only (rule 3b): no key removed or renamed, no value shrunk, every other row byte-identical; `updated_utc` moves forward.
- `tests/test_pipeline_failure_guard.py::test_the_nov15_ledger_rows_are_classified_onto_their_landed_guards` pins the five raised rows against the committed ledger and proves the post-merge gate shape: with all five issues CLOSED the gate verdict is green.

## Impact

- The five issues become closeable WITH PROOF under `make issue-verdict` (issue #993's evidence gate reads these exact rows) — the bot queue stops carrying issues whose class is already fixed and guarded.
- Unblocks the `pipeline-failure-guard-check` gate's future verdicts for these rows; no contract, script, Makefile or gate change.

## Not covered

- The filer quoted regex-artifact lines from PASSING modules: issues #1040–#1043 bodies quote `FAIL: m1: engines not ordered newest-date-first` while the real gate failure was `openspec-index-check` — the line is a planted negative scenario printed by a passing module that the log extractor's error-block regex matched. Filed as a finding by this run's `findings.md`, never fixed inside this keeper (rule 6g).
- No leg stamps `fix_pr` into the ledger when a pipeline-failure fix PR merges (the gap #1067's findings already filed); this keeper is a manual raise, not the mechanism.
