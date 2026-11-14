# Tasks

- [x] 1. The tracked change exists (this directory) before any test edit
- [x] 2. `tests/test_worktree_base.py::run_script` isolates git config by default
      (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`; a caller's
      explicit `env=` entry still overrides)
- [x] 3. `tests/test_worktree_base.py` gains
      `test_rebase_respects_a_configured_checkout_identity` (fixture repo with its
      own `user.email` → no `identity=fallback`, committer stays the repo identity),
      registered in `main()`
- [x] 4. The identity-fallback assertion goes GREEN on THIS host (which has a
      global git identity) — the measured red `PASSED 122 | FAILED 1` becomes
      `PASSED 124 | FAILED 0` — and under a simulated bare environment
      (`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null` on the outer shell)
- [x] 5. Gates green on the exact head: `make lint`, this suite,
      `python3 tests/test_openspec_index.py`, `make openspec-check`,
      `make secret-scan` before push
