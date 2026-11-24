# Tasks: findings-check-shape-gate

- [x] Add `NON_IMPLEMENTATION_BRANCHES` + `implementation_shaped` to `scripts/pr_closure.py`, built only from the parser's existing signals
- [x] Give `scripts/file_findings.py --check` the optional `--event` / `--branch` / `--body-file` shape inputs and the exempt-skip path
- [x] Add `make findings-check-for-pr` and wire it into `qa-validate.yml`'s `validate` job and `scripts/fix_loop.sh`
- [x] Keep the target HOST-SIDE — the python-env container does not mount the runner's `$GITHUB_EVENT_PATH` (measured: PR #1480 run 45288434759) — and pin that with a regression assertion
- [x] Make the analysis visible to CI: drop `findings.md` from `.gitignore` and `scripts/issue_bot_working_files.txt`, updating the same-change tests
- [x] Add the RED-first regression tests for the shape gate and the wiring
- [~] Land the AGENTS.md §6g sentence, the §6b `qa-validate.yml` step and the §8 guard row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Update `ARCHITECTURE.md` target/script rows and regenerate its inventory block + `OPENSPEC.md`
- [x] Run the focused module, `make lint` and the offline gates; write `findings.md`; push for review
