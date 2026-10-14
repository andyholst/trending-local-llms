# openspec/specs

Capability specs that describe what trending-local-llms does **today**.

A change is authored under `openspec/changes/<name>/` (proposal + `specs/<cap>/spec.md`
+ `tasks.md`) and is validated by `make openspec-check` before it can merge. When a
change is implemented, its `specs/<cap>/spec.md` becomes the source of truth for that
capability here.

Every change directory is listed in the root `OPENSPEC.md` index, which
`make openspec-index` regenerates and `make openspec-index-check` keeps honest — an
unlisted change (or a stale reference) fails CI.
