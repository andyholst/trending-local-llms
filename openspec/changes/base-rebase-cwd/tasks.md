# Tasks: base-rebase-cwd

- [x] Refuse a HEAD that is not the named branch in `scripts/worktree_base.py::mode_rebase`
- [x] Add the A/B guard in `tests/test_worktree_base.py`
- [x] Prove the guard RED against the base revision of the seam
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- **RED on the base seam** (`git show origin/master:scripts/worktree_base.py`): `PASSED 153 | FAILED 2` —
  `FAIL rebase: a checkout that is not the branch is REFUSED, never reported up-to-date` with `mode=rebase`
  in the output, i.e. the old code ran and reported `up-to-date` for a branch one commit behind.
- GREEN after: `PASSED 155 | FAILED 0`, including the A/B pair — the second checkout on `master` is
  refused (exit 1, `REFUSED`, HEAD unmoved) while the branch's own worktree reports
  `behind_base=1` / `rebase=rebased`.
- The refusal keeps the exit contract (0 up-to-date/rebased, 3 conflict, **1 refused**, 2 usage);
  the issue's prose said "exit 2" but its own Technical Solution says the contract is unchanged, and
  `Refused` is the seam's refusal path.
- `make lint` and `make architecture-check` green. The §10 inventory regenerated
  (`254 → 256` targets, `101 → 102` scripts) — the fetched base `4818433` carried a stale block.
