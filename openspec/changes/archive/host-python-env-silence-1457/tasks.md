# Tasks: host-python-env-silence-1457

- [x] Silence the `python-env-image` host recipe (`@` + `>&2`), keeping the in-container `@:` escape unchanged
- [x] Extend the workflow redirect guard to a redirected target's prerequisite recipes (RED-verified against the pre-fix head)
- [x] Add the forced-host byte-purity assertions (R1/R2) to `tests/test_pr_body.py`
- [x] Add the host dry-run silence assertion (R3) to `tests/test_python_env_in_container.py`
- [x] Assert the keeper body holds no ensure line (R5) in `tests/test_architecture_bot.py`
- [x] Regenerate `OPENSPEC.md` and run the focused modules, `make lint`, `make architecture-check`, `make openspec-check`
