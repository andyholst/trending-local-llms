# Proposal: security-scan-dispatch-pipeline

Issue: #1185
PR: #1188

## Why

Issue #1175 shipped the five supply-chain scan targets (`make containerfile-scan`,
`make trivy-scan`, `make grype-scan`, `make syft-sbom`,
`make security-scan-self-test`) — verified green locally — but NO workflow calls
any of them: `grep -rn "trivy-scan|grype-scan|syft-sbom|containerfile-scan|security-scan-self-test" .github/workflows/`
returns nothing, which rule 6m forbids ("every `make` target that performs a
verification … MUST be called by a workflow"). Measured at the time of filing, a
Dockerfile base-image pin could sit unpinned and a vulnerable pinned dependency
could sit unflagged forever with no CI job ever looking. The five targets have a
weekly cadence, so they need a pipeline — and the cadence cannot be a cron: the
owner directive of 2026-11-15 (issue #1029, rule 6t) makes `refresh-bot` the ONLY
cron-scheduled pipeline.

## What Changes

- **NEW pipeline `.github/workflows/security-scan.yml`** — dispatch-only (the
  one permitted shape), with the fleet's first job `guard` (rule 6j) and ONE
  `scan` job (`needs: guard`) that runs, through the Makefile only (rule 6m):
  `make containerfile-scan`, `make trivy-scan`, `make grype-scan`,
  `make syft-sbom OUT=…` (+ artifact upload of the SBOM), and
  `make security-scan-self-test` (the planted-vulnerability self-test that
  proves trivy+grype really catch something). Any finding reds the run loudly.
- **The red run is DIAGNOSED and FILED**: `scripts/pipeline_failure_issue.py`'s
  `MAIN_PIPELINES` gains `security-scan.yml`, so a red scan run becomes a
  `tech-debt` issue carrying its scrubbed log error block (rule 6r) on the next
  queued-alarm sweep — the scan report reaches the queue.
- **Test wiring (rules 6c/6m/6j)**: `tests/test_workflows.py` gains
  `BOT_GUARDS["security-scan.yml"]`, a `DISPATCH_ONLY_COVERAGE` row naming the
  five targets it calls, and a wiring test pinning guard-first, `needs: guard`,
  Makefile-only steps, no schedule, and `MAIN_PIPELINES` naming the pipeline.
- **Docs (rules 6h/3c)**: `AGENTS.md` §6b pipeline list gains the
  `security-scan.yml` row in the same commit; `ARCHITECTURE.md` §4 gains the
  pipeline section, §6b the rulebook bullet, and the generated blocks are
  refreshed via `make architecture-refresh`; `make openspec-index` regenerates
  the root index.

## Impact

- Capability: `security-scan` (new spec: dispatch-only cadence, guard, Makefile-only scan steps, red-on-findings, filer reachability).
- Affected: `.github/workflows/security-scan.yml` (new), `scripts/pipeline_failure_issue.py` (additive), `tests/test_workflows.py`, `AGENTS.md` (§6b row — rule 3c review-required), `ARCHITECTURE.md`, `OPENSPEC.md`.
- No data change, no contract change, no new image.

## Not covered

- No cron schedule (rule 6t: only `refresh-bot` may hold one); the cadence is the owner dispatching the pipeline (weekly by convention), and the queued-alarm sweep filing what it finds.
- No new scan targets — all five exist from #1175 (slice 1) and are unchanged here; this change wires them into CI.
- No auto-fix: a finding becomes an issue (rule 6g); the scan pipeline never edits code and never merges anything.
