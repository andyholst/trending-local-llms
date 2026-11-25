# Tasks: profile-provision-backup-skills-1754

- [x] `_backup_file` helper in `scripts/agent_profile_provision.py`: timestamped `*.bak-<UTC>` beside every overwritten lane-home file, `-2`/`-3` collision suffixes, one `[profile-provision] backup …` line per file
- [x] `provision_one` backs up `SOUL.md` and every `skills/**` file before the copy; config backup and summary line unchanged
- [x] Three new guards in `tests/test_agent_profile_provision.py` (skill+SOUL forward bytes, nested + fresh home, repeated provision) wired into `main()`, green on the fix
- [x] Guards RED-proved against the pre-change seam from `origin/master` (forward bytes lost, no backup, no output)
- [x] `make lint`, the full `tests/test_agent_profile_provision.py` module, `make openspec-check` and `git diff --check` green after the last edit
- [x] Tracked change archived on the branch with `Issue: #1754` / `PR: #<n>`, `OPENSPEC.md` regenerated, `findings/1754.md` written
- [x] PR body composed with the five sections and exactly one `Closes #1754`, checked offline with `scripts/pr_body.py --check-body-file <f> --branch fix/profile-provision-skills-backup-1754` (the push/PR/handover themselves are delivery, not a pre-PR gate)
