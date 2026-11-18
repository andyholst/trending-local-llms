## ADDED Requirements

### Requirement: The sweep stamps the landed fix onto a closed pipeline-failure row

When the `queued-alarm` sweep runs `make pipeline-failure-issue`, every ledger row whose issue is CLOSED by exactly one MERGED PR whose diff carries a guard test gains `fix_pr`, `guard`, `merged_utc`, `stamp_utc` and `stamp_note` (additive only — rule 3b), plus ONE marker-deduplicated `pipeline-ledger-stamp` annotation on that issue; the closer is recognized through `scripts/pr_closure.py`'s own closing parser.

#### Scenario: A merged guard-carrying closer raises the row and annotates once

Given a planted ledger entry citing a CLOSED issue and a recorded timeline whose single merged closing PR adds a `tests/` module
When the real filer runs its stamp pass
Then the row carries `fix_pr`, `guard`, `merged_utc`, `stamp_utc` and `stamp_note`, and ONE `pipeline-ledger-stamp` comment is posted

- **Test:** tests/test_pipeline_failure_issue.py::test_a_closed_row_is_stamped_from_the_merged_guard_carrying_pr_that_closed_it

#### Scenario: The guard is the module the merged PR added

Given a merged closer whose diff ADDS `tests/test_the_fix_guard.py` and modifies nothing else
When the stamp pass resolves the row's guard
Then `guard` names the added module

- **Test:** tests/test_pipeline_failure_issue.py::test_the_stamp_prefers_the_guard_module_the_merged_pr_added

#### Scenario: A closer that only modified its guard module still raises the row

Given a merged closer whose diff modifies (not adds) a `tests/test_*.py` module
When the stamp pass runs
Then the row is raised with that module as its guard

- **Test:** tests/test_pipeline_failure_issue.py::test_a_merged_fix_pr_that_only_modified_its_guard_module_still_raises_the_row

### Requirement: An unfinished fix is reported, never guessed

An OPEN issue row, a closing PR not yet merged, a closed issue with no closing PR, an ambiguous close (two merged closers) and a merged close whose diff carries no guard test are reported and left unstamped — the guard gate stays RED on the truly indeterminate shapes instead of laundering them.

#### Scenario: An open issue stays a fix in flight

Given a ledger entry whose issue is OPEN
When the stamp pass runs
Then the row is reported as a fix in flight and written nothing

- **Test:** tests/test_pipeline_failure_issue.py::test_an_open_issue_row_is_reported_as_a_fix_in_flight_never_stamped

#### Scenario: A closing PR not merged yet is retried next sweep

Given a closed-looking row whose closer is recorded but still OPEN
When the stamp pass runs
Then nothing is stamped and the row is reported for the next sweep

- **Test:** tests/test_pipeline_failure_issue.py::test_a_closing_pr_not_merged_yet_is_reported_and_retried_next_sweep

#### Scenario: A closed issue with no closing PR stays the keeper's act

Given a CLOSED issue row whose timeline names no merged closing PR
When the stamp pass runs
Then the row is reported, unstamped

- **Test:** tests/test_pipeline_failure_issue.py::test_a_closed_issue_with_no_closing_pr_stays_the_keeper_s_act

#### Scenario: A merged close without a guard test is refused loudly

Given a merged closer whose diff touches only `scripts/` files
When the stamp pass runs
Then the row stays unstamped and the refusal is printed — the gate remains RED on it

- **Test:** tests/test_pipeline_failure_issue.py::test_a_merged_close_whose_diff_carries_no_guard_test_is_refused_loudly

#### Scenario: One merged closer among several closing PRs is stamped

Given two closing PRs of which exactly one is MERGED and guard-carrying
When the stamp pass runs
Then the row is raised from that merged closer (the unmerged one is noted)

- **Test:** tests/test_pipeline_failure_issue.py::test_the_stamp_raises_the_merged_guarded_close_when_another_closing_pr_is_unmerged

### Requirement: The stamp is idempotent, additive, dry-runnable and ride-through-landable

The pass never overwrites a `guard` the row already records, stamps nothing twice across sweeps, previews in dry mode without writing, survives a per-row read failure by reporting it loudly and retrying next sweep (never a crash, never a fake clean), reports a row citing no issue, and its ledger landing rides the filer's existing ledger-PR path through `make pipeline-failure-issue`.

#### Scenario: An already-raised row is skipped

Given a row whose `fix_pr` is already non-null
When the stamp pass runs a second sweep
Then the row is byte-identical and no second comment is posted

- **Test:** tests/test_pipeline_failure_issue.py::test_the_stamp_never_overwrites_a_guard_the_row_already_records

#### Scenario: Idempotence across sweeps

Given a ledger already stamped by a previous sweep
When the real filer runs the stamp pass again
Then it stamps nothing and posts no duplicate annotation

- **Test:** tests/test_pipeline_failure_issue.py::test_the_stamp_pass_is_idempotent_across_sweeps

#### Scenario: Dry mode previews and writes nothing

Given the filer invoked with `DRY=1`
When the stamp pass runs
Then a `WOULD STAMP` preview is printed and the ledger file is untouched

- **Test:** tests/test_pipeline_failure_issue.py::test_dry_mode_previews_the_stamp_and_writes_nothing

#### Scenario: A failed per-row read is loud but not fatal

Given a recorded `gh api` refusal for one row's timeline
When the stamp pass runs over several rows
Then that row keeps its nulls, the refusal is printed, and the remaining rows still process

- **Test:** tests/test_pipeline_failure_issue.py::test_a_stamp_read_failure_is_loud_on_its_row_and_never_fatal_to_the_sweep

#### Scenario: A row citing no issue writes nothing

Given a ledger entry with `issue: null`
When the stamp pass runs
Then the row is reported and untouched

- **Test:** tests/test_pipeline_failure_issue.py::test_a_row_citing_no_issue_is_reported_and_writes_nothing

#### Scenario: The stamp rides the ledger-PR landing through the Makefile

Given a sweep that stamps rows
When the landing step runs
Then the changed ledger reaches `master` as a ledger PR opened through the same `make pipeline-failure-issue` target (no new target — rule 6m)

- **Test:** tests/test_pipeline_failure_issue.py::test_the_stamp_rides_the_filer_s_ledger_pr_landing_through_the_makefile

### Requirement: A stamped row clears the guard gate only while its named guard exists

`make pipeline-failure-guard-check` reports a stamped CLOSED row as resolved; the same row goes RED again if the guard module it names no longer exists — the stamp satisfies the gate only while the guard is a test on disk.

#### Scenario: The raised row clears the gate

Given a planted CLOSED entry carrying `fix_pr` and a `guard` naming a module under `tests/`
When the real gate verdict runs
Then the entry reports resolved and the verdict exits 0

- **Test:** tests/test_pipeline_failure_guard.py::test_a_closed_row_the_stamp_raised_with_fix_pr_and_guard_clears_the_gate

#### Scenario: A deleted guard re-opens the row

Given a stamped entry whose `guard` names a module that is NOT on disk
When the real gate verdict runs
Then the verdict exits 1 naming the missing guard module

- **Test:** tests/test_pipeline_failure_guard.py::test_a_stamped_row_whose_named_guard_no_longer_exists_is_red
