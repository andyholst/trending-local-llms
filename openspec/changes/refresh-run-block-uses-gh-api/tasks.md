# Tasks: refresh-run-block-uses-gh-api

- [x] `scripts/refresh_run_block.py`: name the argv prefix once (`GH_API = ("gh", "api")`) and use it in `_gh_json`, naming the full command in the failure
- [x] `tests/test_refresh_run_block.py`: `test_the_read_is_a_valid_gh_command` — a stub that answers ONLY `gh api …` and otherwise exits 1 with `unknown command`, so a dropped `api` is RED
- [x] Verified RED on `origin/master`'s composer and GREEN with the fix (same stub, same test)
- [x] Reproduced the production failure on the host against run 38889575999
- [x] Gates green: `make lint`, `make test`, `make openspec-check`, `make architecture-check`
- [x] Commit (Conventional), push the branch, open the PR with `closes #320`; the next scheduled `refresh-bot` run is the production verification
