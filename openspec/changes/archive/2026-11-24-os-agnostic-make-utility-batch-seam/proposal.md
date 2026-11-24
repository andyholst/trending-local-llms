# Proposal: os-agnostic-make-utility-batch-seam

Issue: #1494

## Why

A bot/keeper job on a runner that has Docker but not the pinned Python/deps still runs eight public `make` targets through a bare HOST `python3 scripts/…`, so the runner OS/toolchain leaks into a generated artifact or report. The `$(PYTHON_RUN)` seam from Slice 1 already holds the container harness for the migrated batches; this slice closes the remaining PURE utility batch named by the architect's measured decomposition on #712.

## What Changes

- Route these eight public targets through the ONE `$(PYTHON_RUN)` seam, each keeping its recipe a PURE `python3 scripts/…` command and gaining the `python-env-image` prerequisite: `architecture-refresh`, `openspec-record-pr`, `check-agent-skills`, `agent-skills-report`, `cron-install-check`, `vetted-performance`, `secret-output-report`, `scrub-log`.
- Extend `tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container` with the seeded Slice 4 set, and update the `tests/test_agent_skills.py` pin that asserts the `check-agent-skills` recipe, so the migration is locked by a guard that is RED on the pre-change tree.
- Regenerate `OPENSPEC.md`; no new script, target, pipeline job or image, so `ARCHITECTURE.md` needs no row change.

## Impact

Non-breaking: no schema, contract, API, table or data change. A host with Docker now runs those eight recipes inside the python-env container; the recipe text stays a pure `python3 scripts/…` call. The two `self-archive-*` targets are deliberately NOT routed here — they read the HOST `.git` common dir, so they need a `GIT_COMMON_DIR` mount added to `PYTHON_RUN` first (#712 Slice 4b).

## Not covered

- The `GIT_COMMON_DIR` mount and the `self-archive-snapshot` / `self-archive-guard` targets (#712 Slice 4b).
- gh/GitHub-state-bound targets, host-git identity/worktree targets, image build/selection targets (documented exceptions).
- The `scrubbed_run` host `bash`+`python3` filter and the parse-time `$(shell python3 …)` execs (#712 Slice 5).
