# Tasks: security-scan-dispatch-pipeline (Issue #1185)

- [x] Create `.github/workflows/security-scan.yml`: dispatch-only trigger, first job `guard` (fleet shape), `scan` job `needs: guard`
- [x] Wire the five scan targets into the `scan` job as `make` steps only (containerfile-scan, trivy-scan, grype-scan, syft-sbom + SBOM artifact, security-scan-self-test)
- [x] Extend `scripts/pipeline_failure_issue.py::MAIN_PIPELINES` with `security-scan.yml` (rule 6r)
- [x] Wire the tests: `BOT_GUARDS["security-scan.yml"]`, `DISPATCH_ONLY_COVERAGE` row, new wiring tests in `tests/test_workflows.py` (rules 6c/6j/6m)
- [x] `AGENTS.md` §6b gains the `security-scan.yml` row (rule 3c: the AGENTS.md diff is review-required and announced on the issue and PR)
- [x] `ARCHITECTURE.md` §4 pipeline section + §6b rulebook line; `make architecture-refresh` regenerates the mechanical blocks in the same commit
- [ ] `make openspec-index` current; `make openspec-check`, `make openspec-backlog-check`, `make openspec-binding-check` green
- [ ] `make lint` and `make test` green on the branch
- [ ] Open the PR (`closes #1185`, never draft, five-section body) and monitor its pipeline to green
