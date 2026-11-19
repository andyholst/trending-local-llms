## ADDED Requirements

### Requirement: The sweep reports a diagnosed ledger row that no merged PR attributes

`make pipeline-failure-attribute` with no attestation SHALL print every DIAGNOSED row of
`data/pipeline_failures.json` that names no `fix_pr` — its run id, issue, workflow/job, `targets`
and the reason read from GitHub (`issue #<n> is OPEN`, or CLOSED with no merged closing PR, never a
guess) plus the exact remedy command — SHALL print `unattributed_diagnosed_rows=N`, SHALL write
nothing (no ledger change, no comment), and SHALL exit 0, so the tail the merged-PR stamp pass
(issue #1099) structurally cannot reach is visible on every `queued-alarm` sweep instead of sitting
as a silent null. UNDIAGNOSED rows and terminal `log_expired` drains SHALL be excluded from the
count, because re-diagnosis (issue #987) owns them.

#### Scenario: the stamp pass skips a verdict-held row and the report names it

- **Given** a planted ledger whose row's issue is OPEN under an `agent:refined` verdict hold and a
  recorded `gh` fixture with no merged closing PR
- **When** the stamp pass runs and then the report pass runs
- **Then** the ledger stays byte-identical (the stamp cannot reach it) and the report names the run,
  the issue, the reason and the remedy command
- **Test:** tests/test_pipeline_failure_attribution.py::test_the_stamp_pass_still_skips_an_open_row_and_the_report_names_it

#### Scenario: report mode excludes stamped, expired and undiagnosed rows

- **Given** a planted ledger holding an attributed row, an unattributed diagnosed row, a
  `log_expired` drain and an `undiagnosed` row
- **When** the seam runs with no attestation
- **Then** only the unattributed diagnosed row is printed, the excluded kinds are named as excluded,
  the count is printed, and the ledger on disk is byte-identical
- **Test:** tests/test_pipeline_failure_attribution.py::test_report_mode_excludes_stamped_expired_and_undiagnosed_rows

#### Scenario: a closed row with no closing PR is reported as a manual close, never stamped

- **Given** a diagnosed row whose issue is CLOSED while no merged PR names it in a closing keyword
- **When** the seam runs in report mode
- **Then** the row is reported with that exact shape (a human closed it) and nothing is written
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_closed_issue_with_no_closing_pr_reports_the_manual_close_shape

### Requirement: An attribution raises fix_pr and guard only from a claim that proves itself

With `RUN=` + `FIX_PR=` + `GUARD=` + `EVIDENCE=` all supplied, `make pipeline-failure-attribute`
SHALL raise `fix_pr`, `guard`, `attribution_evidence`, `stamp_utc` and `stamp_note` onto that ONE
row ONLY when: the run exists in the ledger and is diagnosed (an `error_excerpt`, no
`log_expired`); the PR is MERGED on GitHub's own `mergedAt`; the guard is a `tests/test_*.py` module
`make test` collects through the ONE `guard_test_exists` seam the gate reads and carries the named
`::test`; the guard is tied to that fix (the fix PR's own `tests/` diff names it, or the row already
recorded it); and the evidence passes the issue-verdict evidence rule (issue #494) while naming a
path the fix PR touched or its guard module. Any failed condition SHALL refuse with exit 2 and write
NOTHING — no ledger change and no comment — naming the run and the condition.

#### Scenario: a proven attestation stamps a verdict-held row

- **Given** a planted ledger whose row is diagnosed and names no `fix_pr`, and a recorded `gh`
  fixture in which the named PR is merged, its timeline closed nothing, and its `tests/` diff names
  the guard module
- **When** the claim is applied
- **Then** the row carries `fix_pr`, `guard`, `attribution_evidence`, `stamp_utc` and `stamp_note`,
  the exit is 0, and ONE marker-deduplicated `pipeline-attribution` annotation on the issue names
  the fix PR, the guard and why the automatic pass could not reach the row
- **Test:** tests/test_pipeline_failure_attribution.py::test_an_open_verdict_held_row_raises_from_a_merged_guard_carrying_fix

#### Scenario: an unmerged fix PR is refused and nothing is written

- **Given** a diagnosed unattributed row and a recorded fixture in which the named PR is `open`
- **When** the claim is applied
- **Then** the exit is 2, the ledger is byte-identical, no comment is posted, and the refusal names
  the run and the fact that the PR is not merged
- **Test:** tests/test_pipeline_failure_attribution.py::test_an_unmerged_fix_pr_refuses_the_attribution

#### Scenario: a guard the suite does not collect, or does not define, is refused

- **Given** a merged fix PR and a `GUARD=` naming a module `make test` does not collect, or a module
  that exists but does not define the named `::test`
- **When** the claim is applied
- **Then** each is refused at exit 2 with nothing written, naming the collection rule it failed
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_guard_make_test_does_not_collect_refuses_the_attribution
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_named_guard_test_that_the_module_does_not_define_refuses

#### Scenario: a guard the fix PR never touched is refused

- **Given** a merged fix PR whose `tests/` diff names no test file the row's `guard` names, and a row
  that recorded no guard already
- **When** the claim is applied
- **Then** the exit is 2, nothing is written, and the refusal says the guard is untied to the fix
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_guard_the_fix_pr_diff_never_names_refuses_the_attribution

#### Scenario: evidence untied to the fix is refused, including the ledger itself

- **Given** a merged fix PR and a collected guard, and EVIDENCE that (a) names a real path the fix
  PR never touched, (b) is prose naming nothing checkable, (c) cites a path that does not exist in
  the tree, or (d) cites `data/pipeline_failures.json`
- **When** the claim is applied
- **Then** each is refused at exit 2 with nothing written, (d) named as circular
- **Test:** tests/test_pipeline_failure_attribution.py::test_evidence_that_names_nothing_the_fix_touched_refuses
- **Test:** tests/test_pipeline_failure_attribution.py::test_prose_only_evidence_refuses_the_attribution
- **Test:** tests/test_pipeline_failure_attribution.py::test_evidence_citing_a_path_that_does_not_exist_refuses
- **Test:** tests/test_pipeline_failure_attribution.py::test_evidence_citing_the_ledger_itself_is_refused_as_circular

#### Scenario: a claim missing a part is refused before anything is read

- **Given** `RUN=` supplied with `FIX_PR=` or `GUARD=` or `EVIDENCE=` empty
- **When** the seam runs
- **Then** it refuses at exit 2 naming the missing part, and it never silently falls back to report
  mode
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_claim_missing_a_part_is_refused_before_anything_is_read

### Requirement: Attribution is append-only, idempotent, and never rewrites a recorded claim

The seam SHALL only ADD keys. A row that already names a DIFFERENT `fix_pr` SHALL be refused rather
than re-pointed (rule 3b); a row whose recorded `fix_pr` IS the claimed one SHALL be an idempotent
no-op that posts no second comment; every existing key and value (`error_excerpt`, `targets`,
`undiagnosed`, `rediagnosed_utc`) SHALL survive byte-identical; an UNDIAGNOSED row, a terminal
`log_expired` drain, an unknown run and an unreadable ledger SHALL each be refused loudly (exit 2),
never laundered as a clean report.

#### Scenario: a re-claim on a landed attribution is a no-op with one comment

- **Given** a row already attributed to PR `1234` by this seam
- **When** the same claim is applied again
- **Then** the ledger is byte-identical, the output says it was already attributed, and the issue has
  exactly one `pipeline-attribution` comment
- **Test:** tests/test_pipeline_failure_attribution.py::test_the_attribution_is_idempotent_and_marker_deduplicated

#### Scenario: a recorded fix_pr is never replaced

- **Given** a row carrying `fix_pr: 999`
- **When** a claim naming `FIX_PR=1234` is applied
- **Then** the exit is 2, `fix_pr` on disk is still `999`, and nothing is commented
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_row_that_already_names_a_different_fix_pr_refuses_replacing_it

#### Scenario: an undiagnosed or expired row refuses a claim

- **Given** a planted ledger holding an `undiagnosed` row and a `log_expired` drain
- **When** either is named in a claim
- **Then** each is refused at exit 2 naming the pass that owns it (re-diagnosis), and no invented
  `fix_pr` is written
- **Test:** tests/test_pipeline_failure_attribution.py::test_an_undiagnosed_row_refuses_an_attribution_claim
- **Test:** tests/test_pipeline_failure_attribution.py::test_the_terminal_log_expired_drain_refuses_an_attribution

#### Scenario: an unknown run and an unreadable ledger are loud, never a fake clean

- **Given** a claim naming a run id the ledger does not hold, and a planted corrupt ledger
- **When** the seam runs
- **Then** the unknown run exits 2 naming it, and the unreadable ledger exits 2 instead of reporting
  an empty, clean report
- **Test:** tests/test_pipeline_failure_attribution.py::test_an_unknown_run_refuses_the_claim
- **Test:** tests/test_pipeline_failure_attribution.py::test_an_unreadable_ledger_is_exit_2_never_a_fake_clean

### Requirement: An attributed row is what the close gate and the ledger guard accept

A `TRIAGE: close` whose `EVIDENCE:` cites `data/pipeline_failures.json run=<id>` SHALL be accepted by
`scripts/issue_verdict.py` only when that row names a merged `fix_pr` AND a guard `make test`
collects; an unattributed row SHALL keep the close refused. `make pipeline-failure-guard-check` SHALL
keep refusing a CLOSED row with no `fix_pr` and no guard, so a recorded claim is what makes the
expectation satisfiable.

#### Scenario: the close gate accepts the attributed row and refuses the unattributed one

- **Given** a planted ledger with one attributed row (merged `fix_pr` + collected guard) and one
  unattributed diagnosed row
- **When** `scripts/issue_verdict.py` checks a `close` verdict citing each
- **Then** the attributed citation passes and the unattributed citation is refused with exit 2
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_closed_row_with_a_landing_pr_still_needs_ledger_proof_to_close

### Requirement: The marker, the target and the pipeline step are wired once

The `pipeline-attribution` marker SHALL be registered in `scripts/bot_markers.py` (rule 6j) with a
writer in the tree and no second copy of its literal in any other script or workflow step.
`make pipeline-failure-attribute` SHALL be the only way to reach the seam (rule 6m), and
`.github/workflows/queued-alarm.yml` SHALL call it — report mode on every sweep, stamp mode only from
owner-supplied dispatch inputs, annotated with the default `github.token` — after the filer step and
before the step that lands a changed ledger as a reviewed PR (rules 6d/6m).

#### Scenario: the registered marker has its writer and no second copy

- **Given** `scripts/bot_markers.py`, `scripts/pipeline_failure_issue.py` and every workflow under
  `.github/workflows/`
- **When** the marker guard runs
- **Then** `pipeline-attribution` is registered, a writer emits it, and no workflow or second script
  spells its literal
- **Test:** tests/test_pipeline_failure_attribution.py::test_the_registered_marker_has_its_writer_and_no_second_copy_of_the_literal

#### Scenario: the Makefile target and the sweep step are wired

- **Given** the `Makefile` and `.github/workflows/queued-alarm.yml` as checked out in this repo
- **When** the wiring is read
- **Then** the target exists, the sweep calls it through `make` after the filer and before the ledger
  landing, the pipeline carries no `schedule`, and no step reaches the script without `make`
- **Test:** tests/test_pipeline_failure_attribution.py::test_the_makefile_target_and_the_queued_alarm_step_are_wired
- **Test:** tests/test_workflows.py::test_the_attribution_step_runs_before_the_ledger_landing_step

#### Scenario: a workflow that drops the attribution step is red

- **Given** a copy of `queued-alarm.yml` with the attribution step removed (the shape
  `origin/master` held before this change), a copy with the step moved AFTER the ledger landing, and
  a copy whose step reaches `scripts/pipeline_failure_issue.py` without `make`
- **When** the wiring guard runs against each copy
- **Then** all three fail, naming the missing `make pipeline-failure-attribute` call, the wrong
  order, and the Makefile bypass
- **Test:** tests/test_workflows.py::test_a_workflow_that_drops_the_attribution_step_is_red

### Requirement: The rulebook names the attribution seam and its measured rows

`AGENTS.md` §6r SHALL describe the attribution pass and its refusals, and §8 SHALL carry its guard
row naming the measured stranded rows (issues #826/#827/#828, runs 42976201014/42977708147/
43047130543), so a reader who never saw a thread learns which state the pass reports and which
claims it refuses.

#### Scenario: the rulebook rows exist and name the seam

- **Given** `AGENTS.md` as checked out in this repo
- **When** the guard reads §6r and §8
- **Then** the attribution seam, its report mode, its refusal shapes and its measured rows are named
- **Test:** tests/test_pipeline_failure_attribution.py::test_the_rulebook_names_the_attribution_seam_and_the_measured_rows
