# Tasks

- [x] 1. Write the proposal + spec for `ci-output-safety` (issue #346).
- [x] 2. `.github/workflows/issue-bot.yml`: the verdict step captures `OUT=$(make issue-verdict)` and writes only `verdict=…`; no `tee`, no wholesale redirect; the refusal guarantee comes from `bash -e` + a bare assignment.
- [x] 3. `.github/workflows/refresh-bot.yml`: both `rebuild-decision` steps take the same shape (the six decision keys parsed, reasons printed, nothing else written).
- [x] 4. `Makefile`: `issue-verdict` is `@`-silenced, so no consumer inherits the echoed recipe line.
- [x] 5. `scripts/check_secret_output.py`: `whole-stdout-into-output-file` + `whole-stdout-into-log`, with the quoted-argument shape excluded (a pipe inside `"…"` feeds the printer, not the file).
- [x] 6. `tests/test_secret_output.py`: both rules falsified on the measured line and on a command substitution; the parsed shape proven clean; the SHIPPED step executed against a stub `make` (recipe echo + diagnostic + secret-shaped value) proving only `verdict=` reaches `$GITHUB_OUTPUT` and the value reaches neither file nor log; a `make` exiting 2 fails the step.
- [x] 7. `tests/test_issue_triage.py`: the assertion that locked the piped shape now locks the captured one (it was the test keeping the bug in place).
- [x] 8. Guard verified RED on the pre-change tree: 6 violations (3 measured lines × 2 rules) from `git show origin/master:.github/workflows/{issue-bot,refresh-bot}.yml`.
- [x] 9. `AGENTS.md` §3d bullet + §8 row, and the `OPENSPEC.md` index refreshed.
- [x] 10. Gates green: `make lint`, `make check-secret-output`, `make test`, `make validate`, `make architecture-check`, `make secret-scan`, `make openspec-check`.
- [x] 11. Commit, push, open the PR (`closes #346`) — reviewable, never a draft, never merged here.
