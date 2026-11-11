# rebuild-decision

## ADDED Requirements

### Requirement: The rebuild decision is computed once, in tested code

"Rebuild the base image on Sunday, when a ref a consumer reads is missing, or when
forced; the test image on the same Sunday/hash-tag/force rule; the OpenSpec image
when its own tag is missing" MUST be computed in ONE place that tests can drive,
not by inline shell in a workflow.

WHEN a pipeline needs to know whether to rebuild an image, THEN it runs
`make rebuild-decision`, which prints `built`, `test_built`, `publish_openspec`, the
three tags, a `reason` per image and the four published-probes, and the workflow
consumes those lines rather than computing the rule.

#### Scenario: everything current, and not Sunday

- **Given** every ref this revision publishes is on the registry and the day is not Sunday
- **When** the decision runs
- **Then** `built=no`, `test_built=no`, `publish_openspec=no`, every `reason` is `current`, and the tags reported are this revision's
- **Test:** `tests/test_ensure_image.py::test_the_rebuild_decision_is_data_not_workflow_shell`

#### Scenario: an unpublished hash tag rebuilds that image

- **Given** this revision's tags are not published (a merged Dockerfile change)
- **When** the decision runs
- **Then** `built=yes` with `base-tag-missing` in its reason, `test_built=yes` with `test-tag-missing`, and `publish_openspec=yes`
- **Test:** `tests/test_ensure_image.py::test_the_rebuild_decision_is_data_not_workflow_shell`

#### Scenario: a missing consumer `:latest` rebuilds the base

- **Given** the hash tags are published but the `:latest` ref a job pulls is not
- **When** the decision runs
- **Then** `built=yes` with `latest-missing` in its reason, and `test_built=no`
- **Test:** `tests/test_ensure_image.py::test_the_rebuild_decision_is_data_not_workflow_shell`

#### Scenario: Sunday rebuilds both code images, and not the CLI image

- **Given** everything is published and the day is Sunday
- **When** the decision runs
- **Then** `built=yes` and `test_built=yes` with `reason=sunday`, and `publish_openspec=no`
- **Test:** `tests/test_ensure_image.py::test_the_rebuild_decision_is_data_not_workflow_shell`

#### Scenario: force rebuilds the code images only

- **Given** everything is published, not Sunday, and force requested
- **When** the decision runs
- **Then** `built=yes` and `test_built=yes` with `forced` in their reasons, and `publish_openspec=no` (unchanged behaviour)
- **Test:** `tests/test_ensure_image.py::test_the_rebuild_decision_is_data_not_workflow_shell`

### Requirement: An off value is never read as on

The force input MUST be parsed strictly: the strings a caller writes to mean "off"
must not take the rebuild branch, and an unreadable value MUST fail loudly.

WHEN the force value is one of `0`, `false`, `no`, `off` or empty, THEN nothing is
rebuilt; WHEN it is `1`, `true`, `yes` or `on`, THEN the code images rebuild; WHEN
it is anything else, THEN the run fails naming the value.

#### Scenario: zero and false mean off

- **Given** every ref is published and it is not Sunday
- **When** the decision runs with `--force 0`, `false`, `no`, `off` or an empty value
- **Then** `built=no` every time
- **Test:** `tests/test_ensure_image.py::test_force_is_parsed_strictly_so_zero_means_off`

#### Scenario: an unreadable force value fails loudly

- **Given** every ref is published
- **When** the decision runs with `--force maybe`
- **Then** it exits non-zero and says it could not read the value as a boolean
- **Test:** `tests/test_ensure_image.py::test_force_is_parsed_strictly_so_zero_means_off`

### Requirement: The workflow delegates, and a failed decision is loud

`refresh-bot.yml` MUST NOT compute the rule itself, and a failed decision MUST NOT
be able to pass as a green step with empty outputs — every build below is gated on
those outputs, so silence would stop the toolchain from ever rebuilding.

WHEN the workflow's decision steps are read, THEN they run `make rebuild-decision`,
contain no inline `docker manifest inspect` or `date +%u`, set `set -o pipefail`,
and consume only outputs the script prints.

#### Scenario: both decision steps delegate to the tested unit

- **Given** the `build` and `openspec-image` jobs
- **When** their steps are read
- **Then** exactly two steps run `make rebuild-decision`, neither job carries an inline probe or clock, and the Makefile holds the single `date +%u` call site
- **Test:** `tests/test_workflows.py::test_the_rebuild_decision_is_one_tested_unit`

#### Scenario: a piped decision cannot hide a failure

- **Given** both decision steps pipe through `tee` into `$GITHUB_OUTPUT`
- **When** their `run` blocks are read
- **Then** each sets `set -o pipefail`, so a failing decision fails the step instead of reporting tee's status with empty outputs
- **Test:** `tests/test_workflows.py::test_the_rebuild_decision_is_one_tested_unit`

#### Scenario: every consumed output is one the script prints

- **Given** the workflow's `steps.decide.outputs.<name>` references
- **When** they are compared with the keys `decide()` returns
- **Then** each consumed name is printed by the script (this is what catches a renamed key such as `tag` vs `openspec_tag`)
- **Test:** `tests/test_workflows.py::test_the_rebuild_decision_is_one_tested_unit`
