# Tasks: pip-tools-console-script-detection-1593

- [x] Prove the token hole against the real detector: a planted bare `pip-compile`/`pip-tools` in a non-exception public target exits 0 invisible on the pre-change scanner
- [x] Widen `INTERP_RE` to `pip-compile|pip-sync|pip-tools|python3|pip|uv` so each console script is its own token, keeping the near-miss exclusions
- [x] Add the two-polarity property test to `tests/test_os_agnostic_make.py` (planted RED findings with target + line; real harnessed recipes GREEN)
- [x] Reconcile the guard docstring, the `check-no-bare-host-python` target description and `ARCHITECTURE.md` with the new token set
- [x] Prove RED-first against the pre-change tree (6 checks fail there) and GREEN at the head (47/0 in the module)
- [x] Bind this change to `Issue: #1593` / `PR: #1566` so both issues this PR closes are tracked, and regenerate `OPENSPEC.md`
