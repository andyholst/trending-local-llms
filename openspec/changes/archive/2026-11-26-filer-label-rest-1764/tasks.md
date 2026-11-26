# Tasks — filer-label-rest-1764 (issue #1764)

- [x] `scripts/pipeline_failure_issue.py`: replace the `gh issue edit --add-label` fallback with the REST `gh api -X POST repos/<repo>/issues/<n>/labels` write; keep the verify-after-write.
- [x] `tests/test_pipeline_failure_issue.py`: stub-gh answers the REST label write and models the owner PAT's GraphQL refusal behind a fixture flag; add `test_the_label_fallback_uses_rest_when_the_pat_refuses_graphql`.
- [x] RED-first proof: new guard fails on the pre-change script (`PASSED 370 | FAILED 5`, all five from the new test), green on the fix (`PASSED 375 | FAILED 0`).
- [x] OpenSpec change: proposal, `pipeline-failure-filer` spec with Test lines, this checklist; index regenerated.
- [x] `findings/1764.md` records the other four filers still on the GraphQL label path as a separate finding.
- [x] Fast offline gates: targeted module green; `make lint`, `make architecture-refresh` run on the branch head.
- [~] Commit on the issue-named branch, push, open a non-draft PR closing #1764; containerised `make validate` / full `make test` are CI-only — blocked: qa-validate runs on the pushed head.
