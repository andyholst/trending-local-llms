# Tasks: archive-stranded-completed-changes

- [x] Archive `log-tail-honored` with `make openspec-archive` (verified: moved to `openspec/changes/archive/2026-11-12-log-tail-honored/`)
- [x] Archive `per-round-log-capture` with `make openspec-archive` (verified: moved to `openspec/changes/archive/2026-11-12-per-round-log-capture/`)
- [x] Record this repair as its own tracked change and archive it in the same commit (verified: `openspec-archive` moved `archive-stranded-completed-changes`)
- [x] Regenerate `OPENSPEC.md` with `make openspec-index` (verified: index written; `make openspec-index-check` green at this head)
- [x] All §How gates green at this head: `make openspec-check`, `make openspec-archive-check`, `make lint`, `make architecture-check`
