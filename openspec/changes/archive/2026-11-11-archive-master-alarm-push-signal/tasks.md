# Tasks

- [x] 1. The tracked change exists (this directory) before any code lands
- [x] 2. Measured the gap: `python3 scripts/openspec_archive_check.py` on
  `origin/master` at fc16962 flags `master-alarm-push-signal` (issue #527 closed,
  PR #777 merged, no `PR:` line ever recorded); qa-validate run 43014075519
  reds `master` at the OpenSpec gate only
- [x] 3. `make openspec-archive NAME=master-alarm-push-signal` — the change moved
  to `openspec/changes/archive/2026-11-11-master-alarm-push-signal/`
- [x] 4. This change archived in the same commit (its work is complete on this
  branch), so the merge leaves no active change naming a merged PR
- [x] 5. `make openspec-index` regenerated `OPENSPEC.md`
- [x] 6. `make openspec-archive-check` + `make openspec-check` + `make lint`
  green on this branch
