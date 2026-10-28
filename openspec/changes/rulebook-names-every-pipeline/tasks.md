# Tasks

- [ ] 1. The tracked change exists (this directory) before any edit
- [ ] 2. Measured the gap: §6b named 6 of the 12 workflows in `.github/workflows/`
- [ ] 3. `architecture_check.py`: `rulebook_pipelines()` + the two §6b findings (missing workflow, phantom `.yml`), and a missing `AGENTS.md` is a finding
- [ ] 4. Proven to bite on the pre-change `AGENTS.md`: the check named exactly the 6 unlisted pipelines
- [ ] 5. `AGENTS.md` §6b: the heading no longer claims a count; one line per pipeline, each naming its rule; `ARCHITECTURE.md` §4 named canonical for shape
- [ ] 6. `AGENTS.md` rule 6h states that a new workflow must be named in §6b in the same change
- [ ] 7. `AGENTS.md` §8: the `tests/test_architecture.py` row names the §6b guard
- [ ] 8. `ARCHITECTURE.md`: §4's workflow/cron counts corrected (twelve / eight), §6's `architecture_check.py` row states the §6b half
- [ ] 9. `tests/test_architecture.py`: the fixture writes an `AGENTS.md` §6b list; the new case fails on an unlisted workflow and passes when named
- [ ] 10. `make architecture-check`, `make test`, `make lint`, `make validate-mapped` green on the real tree
- [ ] 11. `OPENSPEC.md` regenerated; `make openspec-check` green
- [ ] 12. `findings.md` written
