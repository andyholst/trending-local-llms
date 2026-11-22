# Tasks: pre-change-guard-blob-pin

- [x] Pin the #1182 pre-change blob by SHA in `tests/test_engagement_rollup_1182.py` and fail loudly when it cannot be resolved
- [x] Pin the #1183 pre-change blob by SHA in `tests/test_stale_last_seen_gap.py` and fail loudly when it cannot be resolved
- [x] Prove both guards RED against the pre-change (origin/master-probe) revision on a full clone
- [x] Run `make lint`, the two modules, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- RED on the pre-change tests (full clone, base revision's `tests/`): `test_engagement_rollup_1182.py`
  `FAILED 13 | FAILED 1` and `test_stale_last_seen_gap.py` `FAILED 16 | FAILED 1`, both at the
  `git show origin/master:…` probe.
- RED on an unresolvable pin (loud-failure half): with `PRE_CHANGE_SHA` set to all zeros the guard
  fails `the pinned pre-change blob resolves (never an empty `git show`)` — `FAILED 13 | FAILED 1`,
  never a silent pass.
- The container runs as the image's default user (uid 0, issue #1147) over a checkout owned by the
  invoking uid, so the helper passes `safe.directory` on the COMMAND LINE; both modules are green
  in the container as well as on the host.
