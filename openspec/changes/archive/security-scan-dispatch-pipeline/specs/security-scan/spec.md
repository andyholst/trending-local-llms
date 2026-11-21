# Spec delta: security-scan (NEW capability)

## ADDED Requirements

### Requirement: The supply-chain scan pipeline is dispatch-only and guarded first

The repository SHALL provide exactly one workflow, `.github/workflows/security-scan.yml`, that runs the five supply-chain scan targets. It SHALL trigger only on `workflow_dispatch` (rule 6t: only `refresh-bot` may hold a schedule), and its FIRST job SHALL be the fleet `guard` (rule 6j) with the `scan` job declaring `needs: guard`, so a stranger's dispatch or re-run dies at step one before any scan runs.

#### Scenario: A dispatch runs the guard before the scan

- **Given** a `workflow_dispatch` of `security-scan.yml`
- **When** the workflow graph is evaluated
- **Then** the `guard` job runs first, the `scan` job names `needs: guard`, and `make check-workflow-guards` admits the owner, a write collaborator and the bot while refusing a stranger
- **Test:** tests/test_workflow_guards.py::test_the_real_tree_scans_green_and_covers_every_workflow

#### Scenario: The pipeline carries no schedule

- **Given** `security-scan.yml` in the tree
- **When** the cadence rule (rule 6t) is checked
- **Then** the workflow declares no `on.schedule` and is classified dispatch-only with coverage in `tests/test_workflows.py`
- **Test:** tests/test_workflows.py::test_security_scan_is_dispatch_only_with_named_coverage

### Requirement: The scan job reaches the five targets through the Makefile only

The `scan` job SHALL call exactly the Makefile targets `containerfile-scan`, `trivy-scan`, `grype-scan`, `syft-sbom` and `security-scan-self-test` (rule 6m — no step may reach into `scripts/` directly), and SHALL upload the generated SBOM as a build artifact. Any scanner finding SHALL red the run — a finding is never laundered into a warning.

#### Scenario: Each scan target is invoked as a make step

- **Given** the shipped `security-scan.yml`
- **When** the `scan` job's steps are read
- **Then** each of the five targets appears as a `make <target>` step and no step reaches `scripts/` without `make`
- **Test:** tests/test_workflows.py::test_security_scan_pipeline_is_guarded_dispatch_only_and_runs_the_five_targets

#### Scenario: The scanners prove themselves before the tree is trusted

- **Given** a scan run
- **When** the final step executes
- **Then** `make security-scan-self-test` has required trivy and grype to flag a planted vulnerable fixture (and to pass on a clean tree), so a silently-doing-nothing scanner reds the pipeline instead of reporting a false green
- **Test:** tests/test_workflows.py::test_security_scan_pipeline_is_guarded_dispatch_only_and_runs_the_five_targets

### Requirement: A red scan run is diagnosed and filed by the failure filer

`scripts/pipeline_failure_issue.py`'s `MAIN_PIPELINES` SHALL name `security-scan.yml`, so a scan run that concludes bad on a dispatched sweep is diagnosed from its own log and filed as ONE `tech-debt` issue with the `pipeline-run-failure` marker (rule 6r), and `tests/test_workflows.py`'s classification tables SHALL name the pipeline.

#### Scenario: A failing scan becomes a tracked issue, not a disappeared run

- **Given** a `security-scan.yml` run that concluded `failure`
- **When** the queued-alarm sweep runs `make pipeline-failure-issue`
- **Then** the run is in the filer's main-pipeline set, its failing job's scrubbed error block is extracted, and one marker-deduplicated `tech-debt` issue is filed
- **Test:** tests/test_workflows.py::test_the_failure_filer_watches_the_security_scan_pipeline

### Requirement: The pipeline is documented in the same change

`AGENTS.md` §6b SHALL name `security-scan.yml` with the rule it enforces (rule 6h), and `ARCHITECTURE.md` SHALL describe the pipeline (§4) and regenerate its mechanical blocks, so a reader can find the scan cadence from the rulebook.

#### Scenario: The docs name the pipeline

- **Given** the change's tree
- **When** `make architecture-check` and `make openspec-index-check` run
- **Then** §6b names `security-scan.yml`, §4 describes its jobs and targets, and the generated blocks are current
- **Test:** tests/test_architecture.py::test_real_repo_description_is_current
