# Tasks: check-counter-parity-1301

- [x] Prove the divergence on the pre-change tree: the seam says `FAILED` while plain pytest says `passed` over the same bytes
- [x] Add `scripts/check_counter_parity.py` — the ONE parity implementation (wrap `check()`, read the counter, fail the session)
- [x] Add `tests/conftest.py` registering the plugin, and `tests/test_check_counter_parity.py` with the detector + real-pytest halves
- [x] Wire `check-counter-parity` (internal `_check-counter-parity`) into `make lint`
- [x] RED-verify the guard against `origin/master`'s tree (3 FAIL) and GREEN on this branch (14/0)
- [x] Run `make test`, `make lint`, `make architecture-check`, `make findings-check` and record the real results: `make lint` green (incl. the new `check-counter-parity`), `make architecture-check` green after `make architecture-refresh` + the §3/§6 rows, `make findings-check` green (2 findings); `make test` = **154 passed, 2 FAILED** — `test_check_openspec_tasks.py` (this file's own unticked boxes, the bootstrap) and `test_refusals_land_declaration.py` (passes standalone 45/0; the #1177 anonymous-GitHub-quota flake in the container, PR #1254 already merged for the fix)
- [x] Write `findings.md` (2 findings, `make findings-check` green) — both handed to `tll-planner` rather than fixed inside this change (rule 6g)
- [x] Regenerate `OPENSPEC.md` (`make openspec-index`: 2 active, 417 archived) and commit the change on the branch
- [x] Open the PR (one `closes #1301`) and hand over to `tll-reviewer`; then monitor the pipeline and fix until green — PR #1320, head `42185f6`, `pr-closure` success, `qa-validate` running
