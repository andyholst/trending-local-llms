# openspec-index

## ADDED Requirements

### Requirement: The index keeper's record names the run's real conclusion

`scripts/openspec_index_repair.py::compose_pr_body` MUST NOT claim a run "went red"
unless the cited run's `validate` actually went red. Given the run's conclusion as data
(`run_green` / `index_drift`, from the same `validate.outputs.index_drift` key the
keeper's trigger reads), it MUST render a green-with-drift run as GREEN with the
reported drift count, and a red run with the original wording. The verdict is never
re-decided in the composer (rule 6d), and the body keeps its no-closing-keyword contract
(rule 6e).

#### Scenario: a green-with-drift run never claims a red

- **Given** the measured GREEN post-merge push run `4546683307` on tree `a0f9adc5`, whose `validate` only reported `drift=1`
- **When** the real CLI renders the keeper body with `--run-green --index-drift 1`
- **Then** the body names the run and tree, prints `stayed GREEN` and `drift=1`, and contains no "went red" claim
- **Test:** `tests/test_openspec_index_repair.py::test_the_keeper_body_names_the_green_drift_run_it_repairs`

#### Scenario: a red run keeps the original honest wording

- **Given** the same tree and run URL but a red `validate` (no `--run-green`)
- **When** the real CLI renders the keeper body
- **Then** the body still says the run "went red at the OpenSpec gate" and never claims GREEN
- **Test:** `tests/test_openspec_index_repair.py::test_the_keeper_body_names_the_green_drift_run_it_repairs`

### Requirement: The keeper job's step name and conclusion wiring are true for both triggers

The `index-repair` job's checkout step name MUST describe the tree the run validated,
not a red that a green run never had. Its landing step MUST forward the run's real
conclusion to the body seam via the `validate` output key the trigger already reads
(rules 3d/6d), and no new schedule or cron entry may be introduced.

#### Scenario: the checkout step no longer asserts a red

- **Given** the real `.github/workflows/qa-validate.yml`
- **When** the guard reads the `index-repair` job's checkout step name
- **Then** it contains no "went red" and names the tree the run validated, while the two `failure()`-only sibling keeper steps keep their original names
- **Test:** `tests/test_openspec_index_repair.py::test_the_keeper_body_names_the_green_drift_run_it_repairs`

#### Scenario: the run conclusion reaches the body seam

- **Given** the real `qa-validate.yml` `index-repair` job
- **When** the guard reads its landing step
- **Then** its step `env` carries `RUN_GREEN` derived from `needs.validate.result` and `INDEX_DRIFT` from `needs.validate.outputs.index_drift`, both handed to `make keeper-pr` as body arguments
- **Test:** `tests/test_workflows.py::test_index_repair_job_is_the_event_driven_keeper_for_a_red_master_index_gate`
