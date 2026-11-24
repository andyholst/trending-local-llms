# Tasks: workflow-concurrency-groups-1560

- [x] Add a PR-scoped `concurrency:` group (`cancel-in-progress: true`) to `.github/workflows/qa-validate.yml`
- [x] Add the same group to `.github/workflows/pr-closure.yml`
- [x] Audit all twelve workflows and document every group's scope and cancel choice
- [x] Add `tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group` (RED on the base tree, green here)
- [x] Prove cancellation with two consecutive pushes on a scratch PR (both run ids quoted on #1560)
- [x] Write `findings.md` and regenerate `OPENSPEC.md`
- [x] Run the focused test, `make lint`, `make architecture-check` and `make openspec-check`
