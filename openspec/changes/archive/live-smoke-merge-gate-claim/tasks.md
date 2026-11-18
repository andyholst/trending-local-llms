# Tasks: live-smoke-merge-gate-claim (#1033)

- [x] Open the OpenSpec change (proposal, spec, tasks) from a worktree cut off the fetched
      base (`make worktree-new BRANCH=tech-debt-live-smoke-is-fetch-only-1033 ISSUE=1033`)
- [x] `scripts/architecture_bot.py`: `job_slice` + `job_targets` — "what does ONE job call",
      derived from the existing `_jobs_section`/`_JOB`/`workflow_targets` parser (no second YAML reader)
- [x] `scripts/architecture_check.py`: `model_call_targets()` built from
      `check_secret_output.AGENT_TARGETS_TO_SCRUB` + `hermes-smoke`/`refresh` (rule 6d: one list),
      `_row_call_claims` with the denial exemption, `job_call_findings`, wired into `findings()`
      inside the existing `architecture` stage (no new target — rule 6d/6m)
- [x] `ARCHITECTURE.md` §4 `live-smoke` row rewritten: fetch-only, no model or agent call gates a
      merge (rule 6t, #1029), `hermes-smoke` named only as a DENIAL, and why the job's NAME stays
      (rule 1: branch protection names the required context literally)
- [x] `ARCHITECTURE.md` boundary paragraph updated: §4 now verifies two claim classes
      (cadence wording #1032 and job model-call claims #1033) and still cannot read other prose
- [x] `AGENTS.md` §6b `live-smoke` bullet rewritten to the same truth + new §8 guard row
      (rule 3c: these are the ONLY rulebook sections this change touches — review-required)
- [x] `tests/test_architecture.py`: five new tests — red on the old row shape (rule 6c: the guard
      fires on exactly the shipped wording it exists to refuse), green when the job really calls
      the model, green on a denial, one-list-not-a-copy, shipped tree green — verified:
      `python3 -m pytest tests/test_architecture.py` → 40 passed
- [x] `make architecture-check` green on the corrected tree; `make architecture-refresh` +
      `make openspec-index` regenerated for the changed `scripts/` and the new change
- [x] `make lint` + `make test` green on this branch (host suite; CI re-runs both)
- [x] PR opened with the five-section message pattern and the single `closes #1033` claim
      (`make pr-message-check` OK locally), ready for review, never `--draft`, monitored to green
- [~] Rename the required status context `live-smoke` → a fetch-accurate name — blocked: rule 1, an owner repository-settings act (branch protection names the context literally; no agent or workflow may rewrite it). Reported on issue #1033 instead.
