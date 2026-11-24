## ADDED Requirements

### Requirement: A rebased head is a landed rebase only with proof of scheduled CI

The shared rebaser SHALL report a pushed rebase as verified ONLY when the pushed sha's OWN
`qa-validate.yml` run carries more than zero jobs. It SHALL read that run back from GitHub through
the ONE gh field contract, matching the run on the exact pushed `headSha`, and it SHALL NOT accept
a run belonging to any other sha as proof.

#### Scenario: The rebased head's own run has zero jobs (the #1115 ghost)

- **Given** a behind-and-clean bot branch whose rebased head's qa-validate run concluded with zero jobs
- **When** the pre-squash seam pushes the rebase and reads the new head's run back
- **Then** it prints `verdict=ci-unverified`, leaves `rebased=false` and exits 1, naming the zero-jobs run
- **Test:** tests/test_auto_merge_rebase.py::test_a_rebased_head_whose_run_has_zero_jobs_is_never_reported_as_a_landed_rebase

#### Scenario: The rebased head's own run carries real jobs

- **Given** a behind-and-clean bot branch whose rebased head's qa-validate run carries at least one job
- **When** the pre-squash seam pushes the rebase and reads the new head's run back
- **Then** it prints `verdict=rebased` and `rebased=true`, names the owner-pat push identity and the job count, and exits 0
- **Test:** tests/test_auto_merge_rebase.py::test_a_rebased_head_whose_run_has_zero_jobs_is_never_reported_as_a_landed_rebase

### Requirement: The proof is a contract read, never a best-effort parse

The jobs answer SHALL be read as the shape gh answers (`{"jobs": […]}`); an answer of any other
shape, or one that cannot be read inside the bounded wait, SHALL be reported UNPROVEN rather than
as scheduled CI.

#### Scenario: gh answers an array where the jobs object is expected

- **Given** a planted `run view --json jobs` answer that is an array, not `{"jobs": […]}`
- **When** the pre-squash seam evaluates the rebased head
- **Then** the verdict is UNPROVEN (`rebased=false`, exit 1), never proof
- **Test:** tests/test_auto_merge_rebase.py::test_the_ci_proof_never_reads_a_wrong_shaped_answer_as_scheduled_jobs

### Requirement: The pr-health rebase path holds the same contract

The `pr-health REBASE=1` sweep SHALL apply the same proof to every branch it rebases, so a host
sweep can no more report a clean rebase over a head nothing scheduled than the merge gate can.

#### Scenario: A sweep-rebased head with no scheduled jobs

- **Given** a behind-and-clean bot PR rebased by `make pr-health REBASE=1` whose new head's run carries zero jobs
- **When** the sweep records its outcome for that PR
- **Then** the outcome reads `REBASED but CI UNVERIFIED: …` instead of a bare `REBASED:`
- **Test:** tests/test_pr_health.py::test_the_sweep_rebases_but_reports_unverified_when_the_new_head_scheduled_no_jobs
