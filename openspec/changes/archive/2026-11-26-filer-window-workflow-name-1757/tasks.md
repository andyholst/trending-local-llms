# Tasks — filer-window-workflow-name-1757 (issue #1757)

- [x] `scripts/pipeline_failure_issue.py`: project `workflowName` from REST `name` in the single `_RUN_ROW_FIELDS` mapping
- [x] `tests/test_pipeline_failure_issue.py`: canned REST rows carry the real `name` field, not the non-existent `workflow_name`
- [x] Add RED-first guards: REST name projects workflow name; filed title/ledger name the workflow; dispatch-only run stays tracked (366/366 checks pass)
- [x] RED-prove the guards against the pre-change script (`git show origin/master:...` → 5 FAILs, then restored)
- [x] `scripts/gh_json_fields.py`: drop the stale recorded `workflow_name` read at `window_runs` so `make lint` passes
- [x] OpenSpec change: proposal, `pipeline-failure-filer` spec with Test lines, this checklist; `make openspec-index` regenerated (3 active, 567 archived)
- [x] `findings/1757.md` present; fast offline gates run: `make lint` rc=0, targeted module PASSED 366 | FAILED 0; `make architecture-refresh` ran (block already current)
- [~] Commit on the issue-named branch, push, open a non-draft PR closing #1757; containerised `make validate` / full `make test` are CI-only — blocked: qa-validate runs on the pushed head
