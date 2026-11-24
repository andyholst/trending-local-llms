# Tasks: worktree-base-mode-path-1334

- [x] Add the additive `path=<abs>` line to `mode_check`, to both `mode_advance` branches and to `mode_adopt`
- [x] Pin all four lines with `test_check_advance_and_adopt_name_the_checkout_they_read`, registered in the module's own call list
- [x] Prove the new test RED on the untouched source (`PASSED 155 | FAILED 4`) and GREEN after the fix (`PASSED 159 | FAILED 0`)
- [x] Run `make lint` (rc=0), `make architecture-check` (rc=0), `make findings-check` (14 findings, OK) and `make openspec-index`
- [x] Run the full `make test` and record its own verdict line
- [x] Write `findings.md` (owed §8 row), commit, push a READY PR whose body closes #1334, and hand over to `tll-reviewer`
