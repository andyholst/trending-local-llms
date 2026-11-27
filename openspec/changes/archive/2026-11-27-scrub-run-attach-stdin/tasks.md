# Tasks: scrub-run-attach-stdin

- [x] Add `-i` to the `docker run` in `PYTHON_RUN` (Makefile) so the redactor receives the live pipe
- [x] Add the RED-first guard to `tests/test_scrubbed_run_seam.py` driving the shipped seam + `PYTHON_RUN` against a stand-in Docker CLI — GREEN 20/0 on the fix, RED 15/5 on the base Makefile with the measured `stream: 0 line(s)` → SIGPIPE 141
- [x] Run `make lint`, `make architecture-check` and `make findings-check ISSUE=1808` — all rc 0
- [x] OpenSpec change (proposal bound to `Issue: #1808`, spec with per-scenario tests, tasks) and regenerate `OPENSPEC.md` — 1 active / 597 archived
- [x] Archive the change by name on the branch (`2026-11-27-scrub-run-attach-stdin`); PR number is recorded on the archived proposal after `gh pr create`
- [~] Open the PR with the five-section body and `closes #1808` — blocked: PR number assigned after this gate (headless leg); ticked in the follow-up commit
