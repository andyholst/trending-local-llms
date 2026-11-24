# Tasks: findings-seam-per-issue-1493

- [x] Resolve the analysis file PER ISSUE in `scripts/file_findings.py` through ONE order — explicit `--path`, then `--issue`, then the issue the branch encodes (`pr_closure.implemented_issue`), then the legacy root file
- [x] Stop tracking the shared root `findings.md`: move its historical sections to `findings/history.md`, ignore a stray root write in `.gitignore`, and leave it off `scripts/issue_bot_working_files.txt`
- [x] Forward `ISSUE=` through `make findings-check` so the bot paths and `REQUIRE_FINDINGS`' fix loop resolve `findings/<issue>.md`; give the fix-loop step its `ISSUE`
- [x] Name `findings/<issue>.md` in the implementer/reviewer skills, the three Hermes prompts and the pipeline comments, keeping every existing gate call intact
- [x] Add `tests/test_findings_seam.py`: the REAL resolver, the REAL CLI on a per-issue file, a scratch-repo proof that two siblings touching different issues merge cleanly in BOTH orders, the RED-first premise that the old append point conflicts, and the tree/gate facts
- [~] Add the AGENTS.md §8 guard row for `tests/test_findings_seam.py` — blocked: rule 3c human sign-off (AGENTS.md protected; §8 is off-limits to this dispatch)
- [~] Land the AGENTS.md §6g sentence naming `findings/<issue>.md` instead of the removed root path — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Regenerate `ARCHITECTURE.md`'s inventory block and the root `OPENSPEC.md` index
- [x] Run `tests/test_findings_seam.py`, `tests/test_file_findings.py`, `make lint` and `make architecture-check`; write `findings/1493.md` with the owed-row finding and push for review
