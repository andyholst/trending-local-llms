# data-integrity

## ADDED Requirements

### Requirement: A run stored under two engine names is reported

`make validate` MUST report every (model, source_post, date, t/s) group that carries more than one
engine name, naming both engines, without failing the run.

#### Scenario: the measured pair

- **Given** one post, date and 191 t/s stored under `vLLM` and under `FP4-Local`
- **When** the scan runs
- **Then** it reports the pair, naming the model, both engines and the post
- **Test:** tests/test_duplicate_runs.py::test_one_post_two_engine_names_is_reported

#### Scenario: a placeholder post is not evidence

- **Given** two engines on the same date and t/s but a `https://lightbrd.com/` post
- **When** the scan runs
- **Then** nothing is reported
- **Test:** tests/test_duplicate_runs.py::test_a_placeholder_post_cannot_identify_a_run

#### Scenario: the scan never fails the run

- **Given** the shipped store, which holds 22 such figures
- **When** `validate.py --only data` runs
- **Then** it prints the scan and exits 0
- **Test:** tests/test_duplicate_runs.py::test_the_shipped_store_reports_the_known_pair
