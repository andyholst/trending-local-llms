# merge-queue-rebase

## ADDED Requirements

### Requirement: The ONE rebaser pushes a rebased head with the identity that schedules its CI, and names the identity it used

`scripts/pr_health.py::rebase_and_push` (the ONE rebase implementation used by
`make auto-merge-rebase` and `make pr-health REBASE=1`, rules 6d/6s) MUST push
through `origin` rewritten with `GIT_PUSH_PAT` (the owner PAT the step provides)
when `origin`'s RAW configured URL (`git config --get remote.origin.url` — never
the insteadOf-rewritten `remote get-url`) is a GitHub HTTPS remote; without the
variable the push stays on `origin` exactly as before. Every push names the
identity it used — `push identity: owner-pat` or `push identity: checkout-credential`
— in the seam's output. A job-token push schedules 0 CI jobs on the new head
(issue #1115), so a pipeline that rebases for a merge MUST provide the PAT.

#### Scenario: the seam with GIT_PUSH_PAT pushes via the owner identity

- **Given** a clone whose configured `remote.origin.url` is a GitHub HTTPS URL
  (transport-aliased to a local bare remote for the fixture) and a behind-and-
  clean bot branch
- **When** the real `scripts/auto_merge_rebase.py` runs with `GIT_PUSH_PAT` set
- **Then** it exits with `rebased=true`, its output names `push identity:
  owner-pat`, and the rebased commit is on the origin branch
- **Test:** tests/test_auto_merge_rebase.py::test_rebase_push_carries_the_owner_pat_identity_when_the_step_provides_it

#### Scenario: without GIT_PUSH_PAT the push stays on origin and says so

- **Given** the same fixture without `GIT_PUSH_PAT` (a host sweep, a local remote)
- **When** the real seam rebases and pushes
- **Then** it still rebases and pushes via `origin` and names
  `push identity: checkout-credential`
- **Test:** tests/test_auto_merge_rebase.py::test_rebase_push_carries_the_owner_pat_identity_when_the_step_provides_it

#### Scenario: the pipelines that rebase for a merge provide the PAT, and their reads keep the default token

- **Given** `qa-validate.yml`'s `auto-merge-rebase` step and `pr-health.yml`'s
  rebase-sweep step
- **When** `test_ghost_run_and_push_identity_wiring` scans them
- **Then** each step carries `GIT_PUSH_PAT: secrets.FIXBOT_DISPATCH_TOKEN`, keeps
  its READS on `github.token`, and the ghost sweep step is read-only with the
  default token; `make ghost-run-alarm` is wired through the Makefile (rule 6m)
- **Test:** tests/test_auto_merge_rebase.py::test_ghost_run_and_push_identity_wiring
