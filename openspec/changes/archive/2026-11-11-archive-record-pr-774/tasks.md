# Tasks

- [x] 1. File issue #774 from the observed master red (the archive-check failure on `5c580e4` with the exact guard message quoted as evidence)
- [x] 2. This OpenSpec change exists (proposal + capability spec + this checklist) BEFORE the archive edit (rule 6f)
- [x] 3. Run `make openspec-archive NAME=record-the-pr-on-a-change` — the merged change moves to `openspec/changes/archive/`
- [x] 4. Run `make openspec-index` — `OPENSPEC.md` regenerated (change now listed under `archive/`, not active)
- [x] 5. Regress the guard: `python3 scripts/openspec_archive_check.py` exits 0 after this change (was exit 1)
- [x] 6. `make lint`, `make openspec-check`, `make architecture-check` green on this branch
- [x] 7. `findings.md` written; the change committed and pushed; PR opened with `Closes #774` (ready for review, never a draft, never merged here)
