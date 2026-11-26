# Tasks — search-leg-sigpipe-classify (issue #1747, search-leg shape only)

- [x] `scrubbed_run` reads `PIPESTATUS[0]` and prints the classified `quiet/agent-failed` SIGPIPE failure on exit 141; producer status and capture contract unchanged
- [x] Guard wired into `tests/test_os_agnostic_make.py::main()` — RED on the old macro, GREEN on this head (PASSED 66 | FAILED 0)
- [x] `bash -n` syntax check on the expanded macro (rc=0)
- [x] OpenSpec change with proposal, capability spec + Test line, all tasks ticked; index regenerated
- [x] `findings/1747.md` declares the owed AGENTS.md §8 row to the attended owner (rule 3c)
- [x] Fast offline checks green; containerised `make validate` / `live-smoke` are CI-only — blocked: qa-validate runs on the pushed head
