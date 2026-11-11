# Tasks

- [x] 1. Write the proposal + `pr-body` capability spec for issue #542.
- [x] 2. `scripts/pr_body.py`: `refresh_body(window)` and `architecture_body(run_url)` behind `--for refresh|architecture`; `--issue` is no longer required for those modes.
- [x] 3. An empty/unreadable window is REFUSED (a blank first section is the #199 defect); an architecture body carrying a closing claim raises.
- [x] 4. `make refresh-pr-body [WINDOW_FILE=…]` and `make architecture-pr-body RUN_URL=…`, both `@`-silenced.
- [x] 5. `refresh-bot.yml` redirects the target into `$PR_BODY`; `architecture-bot.yml` pipes it into `gh pr create`; both inline bodies are gone.
- [x] 6. `tests/test_pr_body.py::test_the_other_two_pr_bodies_are_composed_too` (35 passed).
- [x] 7. `ARCHITECTURE.md` rows for both targets; `make openspec-check`, `make architecture-check`, `make lint` green.
