# Tasks: archive-stranded-completed-changes-907

- [x] Archive `land-the-owed-rulebook-rows` with `make openspec-archive` (verify: moved to `openspec/changes/archive/`)
- [x] Archive `the-owed-section-8-rows` with `make openspec-archive` (verify: moved)
- [x] Archive `captured-recipe-is-silent` with `make openspec-archive` (verify: moved)
- [x] Archive `one-queue-reader` with `make openspec-archive` (verify: moved)
- [x] Archive `index-failure-names-its-cause` with `make openspec-archive` (verify: moved)
- [x] Record this keeper as its own tracked change and archive it in the same commit (precedent shape)
- [x] Regenerate `OPENSPEC.md` with `make openspec-index` (verify: `make openspec-index-check` green at this head)
- [x] All gates green at this head: `make openspec-check`, `make lint`, `make architecture-check`, `make test`
