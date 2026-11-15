# alarms

## ADDED Requirements

### Requirement: An issue-bot run that reded the trending-for-your-card guard is closed on a re-diagnosed ledger row

A main-pipeline failure that died at `make test` on `tests/test_trending_for_your_card.py`
(the datacenter-aggregate real-store assertion) MUST be tracked by the failure filer, and —
the class being fixed and guarded by the landed `in_scope()` speed-gate (issue #349, PR #571,
`tests/test_trending_for_your_card.py`) — its UNDIAGNOSED ledger row MUST be raised append-only
naming that `fix_pr` and `guard`, quoting the bounded error block (`error_excerpt`) and keeping
the original `undiagnosed` field, so the tracked issue closes on ledger proof and
`make pipeline-failure-guard-check` stays green after the close (rule 6r).

#### Scenario: the issue-bot row names the landed trending guard

- **Given** the committed ledger row for run 43050447566 (issue #830), filed UNDIAGNOSED by the
  pre-#923 log reader and re-diagnosed by the #969 seam to show the `make test` red at
  `tests/test_trending_for_your_card.py` ("Qwen3.8-27B's speed bonus is not the 28,340 t/s
  datacenter aggregate", `targets: ["test"]`)
- **When** the row lists the landed fix for that class on the fetched base
- **Then** the row names `fix_pr: 571` and `guard: "tests/test_trending_for_your_card.py"` — a
  module `G.guard_test_exists` accepts and that runs `PASSED 45 | FAILED 0` on HEAD — keeps the
  original `undiagnosed` field, and leaves `targets` unchanged (rule 3b)
- **Test:** tests/test_pipeline_failure_guard.py::test_run_43050447566_is_rediagnosed_onto_the_landed_trending_guard

#### Scenario: the sibling issue closed on that row passes the ledger gate

- **Given** the committed ledger with issue #830 CLOSED beside its re-diagnosed siblings
- **When** `scripts/pipeline_failure_guard_check.py` verdicts the ledger
- **Then** the gate exits 0 — a closed row names a real fix PR and a guard test on disk, so the
  close is guarded, not laundered
- **Test:** tests/test_pipeline_failure_guard.py::test_run_43050447566_is_rediagnosed_onto_the_landed_trending_guard
