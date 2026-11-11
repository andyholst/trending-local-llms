# Tasks: ci-secret-output-guard

- [x] Add `scripts/check_secret_output.py` (llgenie port, adapted to this repo's secret-shaped variables)
- [x] Add `tests/test_secret_output.py` — one test per rule, plus the pass-on-this-repo self-test
- [x] Add the wiring test `tests/test_workflows.py::test_secret_output_guard_wired_into_qa_validate`
- [x] Add `make check-secret-output` + `make secret-output-report` (named in ARCHITECTURE.md)
- [x] Wire `tests/test_secret_output.py` into `make test`'s `_test` fallback chain
- [x] Add `make check-secret-output` step to `qa-validate.yml`'s `validate` job
- [x] Update AGENTS.md rule 3d + §8 guard row; issue #219 carries the rule-3c comment
- [x] Update ARCHITECTURE.md (script, targets, workflow step; rule 6h)
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`)
- [x] Gates green: `make lint`, `make _test`, `make secret-scan`, `make architecture-check`, `make openspec-check`
- [x] Commit (Conventional), push branch, open the PR with `closes #219`; qa-validate green on the PR is the final verification
