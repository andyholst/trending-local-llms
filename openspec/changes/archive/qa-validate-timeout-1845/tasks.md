# Tasks: qa-validate-timeout-1845

- [x] `.github/workflows/qa-validate.yml:131` `timeout-minutes: 30` → `45` on the `validate` job only — one-line diff; no schedule, other job timeout, new workflow, data, README or schema change
- [x] `tests/test_workflow_guards.py` gains a real assertion reading the shipped YAML and pinning `validate.timeout-minutes == 45`, wired into `main()` — RED on base (rc=1, `timeout-minutes=30`), GREEN on fix (48 passed, 0 failed)
- [x] Existing workflow-guard assertions stay green on the fixed tree — the real-tree scan, guard caller classes, lint wiring and fixture escapes all pass
- [x] `findings/1845.md` written with Evidence / Why / Done when for the cancelled-at-30m run
- [x] OpenSpec change (`.openspec.yaml`, proposal, Given/When/Then capability spec with resolving `Test:` lines, every task box ticked) added and `OPENSPEC.md` regenerated
- [x] Fast offline checks only: targeted workflow-guard module, `make lint`, OpenSpec index/spec-test/tasks checks, archive check and findings shape check
- [x] One READY PR with the five-section body and `Closes #1845` in both title and body; no merge, master push, label or schedule change
