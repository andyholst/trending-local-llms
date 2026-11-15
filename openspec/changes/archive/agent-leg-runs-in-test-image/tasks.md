## Tasks — issue #833: agent legs that self-verify run in the TEST image

### Makefile wiring

- [x] `implement-issue` runs the agent via `$(TEST_RUN)` (TEST image) instead of `$(DOCKER_RUN)` (base)
- [x] `review-issue` runs the agent via `$(TEST_RUN)` instead of `$(DOCKER_RUN)`
- [x] `review-issue-window` runs the agent via `$(TEST_RUN)` instead of `$(DOCKER_RUN)`
- [x] `fix` runs the repair agent via `$(TEST_RUN)` instead of `$(DOCKER_RUN)`
- [x] the non-verifying search legs (`search-nvidia/metal/cpu/amd`) stay on `$(DOCKER_RUN)` — they never run the canonical suite

### Guard tests

- [x] `tests/test_implement_stream.py` pins the four agent legs to `$(TEST_RUN … make _setup && make _<leg>)` (the test-capable image), not `$(DOCKER_RUN …)`
- [x] `tests/test_workflows.py` pins `implement-issue` to the `$(TEST_RUN)` seam shape
- [x] `tests/test_search_budget.py` pins the `fix` wrapper to the `$(TEST_RUN)` seam shape (it forwards `HERMES_FIX_REASONING` into the container either way)
- [x] a regression guard asserts `markdown-it-py` is declared in `requirements-test.in` (test image only) and NOT in `requirements.in` (base) — the precondition that makes the base image the wrong environment for a self-verifying leg

### Docs + validation

- [x] `make test` green (`test_implement_stream`, `test_workflows`, `test_search_budget` and the new guard pass)
- [x] `make validate` green (the canonical suite runs in the TEST image unchanged)
- [x] `make openspec-check` green (this change: proposal + GWT spec + tasks, issue-bound, indexed)
- [x] `make architecture-check` green (ARCHITECTURE.md kept true for the four legs' runtime image)

### Repo-level

- [x] REGISTER this guard on the pipeline-failure ledger row for run 43110467252: `data/pipeline_failures.json` names `guard` = `tests/test_implement_stream.py` (additive; `fix_pr` lands when PR #833 opens), so `make pipeline-failure-guard-check` can close issue #833 legitimately
- [~] Add the AGENTS.md §8 guard row for `tests/test_implement_stream.py` (the four self-verifying agent legs + the markdown-it-py test-image-only manifest split) — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg; the full row text is declared in findings.md as an owed-row)
