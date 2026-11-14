# Tasks: bot-pr-rebaser-818

- [x] `scripts/pr_health.py`: pure `rebase_plan()` (bot `ci/` prefix, CONFLICTING
      never auto-rebased, drafts untouched) + git half (`fetch_base`,
      `branch_behind`, scratch-worktree `rebase_and_push` with
      `--force-with-lease` pinned to the fetched tip, `run_rebaser`) behind
      `--rebase` / `--dir` — verified: `python3 tests/test_pr_health.py`
      (56 checks, 0 failed)
- [x] `Makefile`: `_pr-health` / `pr-health` forward `REBASE=1` → `--rebase`
      (empty by default: the report-only shape is byte-identical) — verified:
      `make lint` + the wiring check in `tests/test_pr_health.py`
- [x] `.github/workflows/pr-health.yml`: sweep step runs
      `make pr-health REPO=… COMMENT=1 REBASE=1`; sweep job `contents: write`;
      checkout `fetch-depth: 0` — verified: `make check-workflow-guards` green
      and `tests/test_workflows.py` green
- [x] `tests/test_pr_health.py`: `test_rebase_plan_classifies_by_ownership_and_conflict`
      + real-git end-to-end (bare origin + clone, only `gh` stubbed — rule 6m)
      + rebaser wiring assertions in the existing wiring test — verified: the
      file passes end to end against planted branches (rebased branch gains
      `origin/master` as ancestor; human, CONFLICTING, current and master OIDs
      byte-identical)
- [x] `AGENTS.md` §6r mechanical-half line + §6b `pr-health.yml` bullet state the
      rebaser (rule 3c: sections named in the issue's start comment; the diff is
      review-required) — verified: `tests/test_architecture.py` green
- [x] `ARCHITECTURE.md` inventory block regenerated — verified:
      `make architecture-check` green
- [x] OpenSpec change created with proposal + `specs/pr-sweep-rebase/spec.md` —
      verified: `make openspec-check` green
- [~] PR opened, pipeline monitored to green — blocked: the merge is qa-validate's
      `auto-merge` gate (green `validate` + `live-smoke` at head) and the AGENTS.md
      §6r/§6b/§8 diff is rule-3c review-required; the change never merges itself
