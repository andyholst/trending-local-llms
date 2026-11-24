# Tasks: rulebook-fleet-handover-1363

- [x] Cut `rulebook-fleet-handover-1363` from freshly fetched `origin/master` (`109cc08241e7129cd0aea6feaae33eeeb7e3455d`, measured this session) in its own worktree
- [x] Land the §8 row extension IN PLACE verbatim from the reviewer-approved verdict (issuecomment carrying the corrected 1929-char row; master's `24 had none` wording preserved, cell 1 byte-identical, one line replaced by one line)
- [x] Add the one names-only pin `test_section_8_row_names_the_1361_generated_artifact_guard` and register it in the existing `main()` — RED on base / GREEN on target / reverse-RED verified by execution
- [x] Add no §7b bullet and no `Rule 3c note` clause; touch neither the #1482/#1589 rows nor the #1586/#1602 modules
- [x] Regenerate `OPENSPEC.md`; keep the OpenSpec checks green
- [x] Run the fast offline checks only; the containerised `make validate`, whole `make test` and `make live-smoke` stay CI-only
