# Spec delta: ci-pipelines (openspec-image publish gating)

## ADDED Requirements

### Requirement: refresh-bot builds the OpenSpec image exactly when its hash tag is missing

The `openspec-image` job of `refresh-bot.yml` SHALL build and push the multi-architecture OpenSpec CLI image when `make rebuild-decision` reports `publish_openspec=yes` (its content-hash tag is missing — the same polarity as the base image's `built=yes`), and SHALL skip the build (reuse the published tag) when `publish_openspec=no`. `make openspec-manifest-check` SHALL run on both paths against the decision's exact tag.

#### Scenario: a merged openspec/Dockerfile change publishes its new tag

- **Given** a refresh run whose `rebuild-decision` answered `publish_openspec=yes` with `openspec_reason=openspec-tag-missing`
- **When** the `openspec-image` job runs
- **Then** the `Build + push the OpenSpec image` step executes (multi-arch, tags `latest` + the hash tag), and `openspec-manifest-check` verifies the tag that was just published
- **Test:** tests/test_workflows.py::test_the_rebuild_decision_is_one_tested_unit

#### Scenario: a current tag is reused, not rebuilt

- **Given** a refresh run whose `rebuild-decision` answered `publish_openspec=no` (hash tag already published)
- **When** the `openspec-image` job runs
- **Then** the build step is skipped, the `already current` step states the reuse, and `openspec-manifest-check` still verifies the published tag's manifest
- **Test:** tests/test_workflows.py::test_the_rebuild_decision_is_one_tested_unit

#### Scenario: the inversion cannot return silently

- **Given** a workflow edit that gates the OpenSpec build on `publish_openspec == 'no'` again
- **When** `make test` runs
- **Then** the step-name-keyed pins fail, naming each step's actual `if`
- **Test:** tests/test_workflows.py::test_issue_bot_files_findings_only_when_green
