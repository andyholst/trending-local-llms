# Tasks

- [x] 1. Write the proposal + spec for `bot-agent-run-safety` (issue #357).
- [x] 2. `Makefile`: all four `_search-*` prompts name `\$${FIRECRAWL_API_KEY}` as an instruction (never a value, never an elided name), with the sentence that says it is the environment variable and must not be printed.
- [x] 3. `scripts/require_env.py`: exit 2 when a named variable is missing OR empty (never printing a value), naming the variable and how to set the secret; `--allow-unconfigured` is a loud local opt-out.
- [x] 4. `Makefile`: `_search-preflight` (`require_env.py` + the existing `search-smoke`) run FIRST by `search-nvidia`, `search-metal`, `search-cpu`, `search-amd` and `search`.
- [x] 5. `skills/gather-data.md`: the header comes from the environment and is never printed; a `401` is a BLOCKER to report, not a reason to hunt for a key.
- [x] 6. `tests/test_search_key.py`: the four prompts name the real variable and carry no elided form; the escaping proven at the SHELL level (name present, value absent); every public leg runs the pre-flight; `require_env.py` passes on set and fails on missing/empty without printing the value; the opt-out never reaches a workflow.
- [x] 7. `tests/test_amd_backend.py`: the wrapper assertion locks the new two-line shape (pre-flight + seam) — the test that caught the change (rule 6b).
- [x] 8. `tests/test_search_key.py` wired into `make test` (rule 6d).
- [x] 9. `AGENTS.md` §3d bullet + §8 row; `ARCHITECTURE.md` (the script, the pre-flight, the search target rows); `OPENSPEC.md` index refreshed.
- [x] 10. `findings.md` written and `make findings-check` green (rule 6g).
- [x] 11. Gates green: `make lint`, `make check-secret-output`, `make secret-scan`, `make test`, `make validate`, `make architecture-check`, `make openspec-check`.
- [x] 12. Commit, push, open the PR (`closes #357`) — reviewable, never a draft, never merged here.
