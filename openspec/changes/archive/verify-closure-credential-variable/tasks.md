# Tasks: verify-closure-credential-variable

- [x] Add `credential_variable()` (`GH_TOKEN`, else `GITHUB_TOKEN`) to `scripts/verify_closure.py`
- [x] Name that VARIABLE in `_gh`'s refusal beside the command, the exit code and gh's stderr — no value printed (rule 3d)
- [x] Drive the REAL `_gh` against a stub `gh` under both spellings, asserting the named variable and the absence of any value
- [x] Pin the base revision's refusal RED/GREEN by running `origin/master`'s own script through the same stub
- [~] Append the §8 row for `tests/test_verify_closure.py` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); declared in findings/1695.md
- [x] Update the two `verify-closure` rows in `ARCHITECTURE.md`
- [x] Write `findings/1695.md` and open the PR ready for review
