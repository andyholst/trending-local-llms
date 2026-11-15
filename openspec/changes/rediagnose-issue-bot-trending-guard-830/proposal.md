# Re-diagnose the issue-bot trending-guard row (issue #830)

Issue: #830

## Why

Issue #830 was filed UNDIAGNOSED: the pre-#923 log reader refused the job log of
`issue-bot` implement run 43050447566 (job 130626253107), so its ledger row carries
`fix_pr: null` and `guard: null` (rule 6r shape unmet). The log is readable now — the
re-diagnosis seam (#969, `filer-rediagnosis-seam-969`) already re-read the run on this
sweep and raised `error_excerpt`: the implement leg's `make test` reded
`tests/test_trending_for_your_card.py` at the real-store assertion "Qwen3.8-27B's speed
bonus is not the 28,340 t/s datacenter aggregate" (`targets: ["test"]`). That is the exact
datacenter-aggregate class issue #349 describes, fixed and guarded on the fetched base by
PR #571 (`in_scope()` never admits a datacenter bump to the speed term), measured green at
both the run's own base commit (d3d411632) and HEAD (`python3
tests/test_trending_for_your_card.py` → `PASSED 45 | FAILED 0` twice-verified). An
UNDIAGNOSED row of a class that is already fixed and guarded must be re-diagnosed onto the
landed fix, not left open as prose (rule 6r).

## What Changes

- The ledger row for run 43050447566 is raised append-only: `fix_pr: 571`,
  `guard: "tests/test_trending_for_your_card.py"`, a `rediagnosis_note` quoting the landed
  fix and the verified guard, `targets` already `["test"]` (the log names it — rule 3b growth
  only); the original `undiagnosed` field KEPT.
- `tests/test_pipeline_failure_guard.py` gains
  `test_run_43050447566_is_rediagnosed_onto_the_landed_trending_guard` asserting the row and
  the post-merge gate shape with #830 CLOSED.
- The root `OPENSPEC.md` index is regenerated (it was already stale by the count line at
  HEAD, 307 vs 309 archived — index-only drift the regeneration fixes).

## Impact

- `data/pipeline_failures.json` — one row raised (added keys, nothing removed).
- `tests/test_pipeline_failure_guard.py` — one test function + its `main()` call.
- `OPENSPEC.md` — regenerated (count line + this change's row).
- Affected capability: `alarms`.

## Not covered

- No repo-side behavioural fix: the guard stands and is green on the fetched base; the only
  gap is ledger bookkeeping that lets this tracked run close on ledger proof instead of
  staying open as prose (rule 6r).
